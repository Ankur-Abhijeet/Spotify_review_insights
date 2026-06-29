import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.scrapers.play_store import PlayStoreScraper
from backend.scrapers.app_store import AppStoreScraper
from backend.scrapers.reddit import RedditScraper
from backend.scrapers.spotify_community import SpotifyCommunityScraper

from backend.analysis.preprocessor import Preprocessor
from backend.analysis.llm_client import LLMClient
from backend.analysis.prompts import get_analysis_prompt
from backend.analysis.aggregator import Aggregator
from backend.utils.logger import get_logger
from backend.utils.usage_tracker import get_usage

logger = get_logger(__name__)
router = APIRouter(prefix="/api")

# Global in-memory session database
SESSION_DB = {
    "scraped": [],
    "preprocessed": [],
    "analyzed": [],
    "aggregated": {},
    "usage": {}
}

class ScrapeRequest(BaseModel):
    sources: List[str]
    limits: Dict[str, int]

class PreprocessRequest(BaseModel):
    keywords: List[str]

class AnalyzeRequest(BaseModel):
    limit: int

@router.post("/scrape")
async def run_scrape(request: ScrapeRequest):
    logger.info("[Pipeline] Running synchronous scrape...")
    scrapers = []
    limits = request.limits
    
    if "all" in request.sources or "play_store" in request.sources:
        scrapers.append((PlayStoreScraper(), limits.get("play_store", 10)))
    if "all" in request.sources or "app_store" in request.sources:
        scrapers.append((AppStoreScraper(), limits.get("app_store", 10)))
    if "all" in request.sources or "reddit" in request.sources:
        scrapers.append((RedditScraper(), limits.get("reddit", 10)))
    if "all" in request.sources or "spotify_community" in request.sources:
        scrapers.append((SpotifyCommunityScraper(), limits.get("spotify_community", 10)))
        
    tasks = [scraper.scrape(limit=limit) for scraper, limit in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    raw_records = []
    for r in results:
        if isinstance(r, list):
            raw_records.extend(r)
        else:
            logger.error(f"[Pipeline] Scraper failed: {r}")
            
    SESSION_DB["scraped"] = raw_records
    
    # Reset downstream steps
    SESSION_DB["preprocessed"] = []
    SESSION_DB["analyzed"] = []
    SESSION_DB["aggregated"] = {}
    
    return {"status": "completed", "total": len(raw_records)}

@router.post("/preprocess")
async def run_preprocess(request: PreprocessRequest):
    logger.info("[Pipeline] Running synchronous preprocess...")
    if not SESSION_DB["scraped"]:
        raise HTTPException(status_code=400, detail="No scraped data found. Run Step 1 first.")
        
    preprocessor = Preprocessor()
    try:
        preprocessed = await preprocessor.process_records(SESSION_DB["scraped"], request.keywords)
        SESSION_DB["preprocessed"] = preprocessed
        
        # Reset downstream step
        SESSION_DB["analyzed"] = []
        SESSION_DB["aggregated"] = {}
        
        return {"status": "completed", "total": len(preprocessed)}
    except Exception as e:
        logger.error(f"[Pipeline] Preprocess failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def run_analyze(request: AnalyzeRequest):
    logger.info(f"[Pipeline] Running synchronous analyze (limit: {request.limit})...")
    if not SESSION_DB["preprocessed"]:
        raise HTTPException(status_code=400, detail="No preprocessed data found. Run Step 2 first.")
        
    records_to_analyze = SESSION_DB["preprocessed"][:request.limit]
    
    # Batch the requests to keep prompt size small, preventing rate limits (429) and timeouts (30s)
    batch_size = 5
    batches = [records_to_analyze[i:i + batch_size] for i in range(0, len(records_to_analyze), batch_size)]
    
    client = LLMClient()
    merged_analyzed = []
    failed_batches_count = 0
    
    for idx, batch in enumerate(batches):
        logger.info(f"[Pipeline] Processing LLM batch {idx + 1}/{len(batches)} (size: {len(batch)})...")
        prompt = get_analysis_prompt(batch)
        
        try:
            response = await client.generate_json(prompt)
            analyzed = response.get("reviews", [])
            
            # Merge LLM output with original records to preserve source, body, rating, date
            original_map = {str(r.get("review_id")): r for r in batch}
            
            batch_results_count = 0
            for a in analyzed:
                rid = str(a.get("review_id"))
                if rid in original_map:
                    # Merge: original data first, then LLM overwrites/adds new fields
                    merged = {**original_map[rid], **a}
                    merged_analyzed.append(merged)
                    batch_results_count += 1
                else:
                    merged_analyzed.append(a)
            
            # If the LLM returned empty reviews list or fallback mock reviews (which usually have unknown/None IDs),
            # we check if it is mock fallback. Standard fallback has segment "unknown" and theme "General Feedback".
            # If we only got 1 mock fallback with no matching ID, we count it as a partial engine failure.
            if len(analyzed) == 1 and str(analyzed[0].get("review_id")) not in original_map:
                logger.warning(f"[Pipeline] Batch {idx + 1} returned mock fallback data instead of real LLM output.")
                failed_batches_count += 1
            else:
                logger.info(f"[Pipeline] Batch {idx + 1} processed successfully. Extracted {batch_results_count} reviews.")
                
        except Exception as e:
            logger.error(f"[Pipeline] Batch {idx + 1} failed: {e}")
            failed_batches_count += 1
            
    # If all batches failed or fell back to mock data
    if failed_batches_count == len(batches) and len(batches) > 0:
        raise HTTPException(
            status_code=500, 
            detail="All AI analysis batches failed or fell back to mock data. Please verify your Groq API key and rate limits."
        )
        
    SESSION_DB["analyzed"] = merged_analyzed
    
    # Reset downstream states
    SESSION_DB["aggregated"] = {}
    SESSION_DB["indexed"] = False
    
    return {"status": "completed", "total": len(merged_analyzed), "failed_batches": failed_batches_count}

@router.post("/aggregate")
async def run_aggregate():
    logger.info("[Pipeline] Running synchronous aggregate...")
    if not SESSION_DB["analyzed"]:
        raise HTTPException(status_code=400, detail="No analyzed data found. Run Step 3 first.")
        
    try:
        agg = Aggregator()
        aggregated = agg.aggregate(SESSION_DB["analyzed"])
        SESSION_DB["aggregated"] = aggregated
        SESSION_DB["usage"] = get_usage()
        
        return {"status": "completed", "summary": aggregated.get("summary", {})}
    except Exception as e:
        logger.error(f"[Pipeline] Aggregate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index-chat")
async def run_index_chat():
    logger.info("[Pipeline] Running synchronous index for Chatbot...")
    if not SESSION_DB["analyzed"]:
        raise HTTPException(status_code=400, detail="No analyzed data found. Run Step 3 first.")
        
    from backend.rag.chat_service import ChatService
    try:
        chat_service = ChatService()
        chat_service.retriever.index_records(SESSION_DB["analyzed"])
        SESSION_DB["indexed"] = True
        return {"status": "completed", "total_indexed": len(SESSION_DB["analyzed"])}
    except Exception as e:
        logger.error(f"[Pipeline] Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-llm")
async def test_llm_connection():
    client = LLMClient()
    result = {
        "engine": client.engine,
        "groq_key_configured": bool(client.groq_api_key),
        "groq_key_prefix": client.groq_api_key[:7] if client.groq_api_key else None,
        "primary_model": client.primary_model
    }
    
    # Try calling Groq directly (bypassing the Ollama fallback) so we see the raw Groq error
    if client.engine == "groq":
        try:
            response = await client._call_groq("Respond with JSON: {\"status\": \"success\"}")
            result["groq_status"] = "success"
            result["response"] = response
        except Exception as e:
            import traceback
            result["groq_status"] = "failed"
            result["groq_error"] = str(e)
            result["groq_traceback"] = traceback.format_exc()
    else:
        result["groq_status"] = "skipped (engine is not set to groq)"
        
    return result

@router.get("/pipeline-preview")
async def get_pipeline_preview():
    return {
        "scraped": {
            "total": len(SESSION_DB["scraped"]),
            "sample": SESSION_DB["scraped"][:10]
        },
        "preprocessed": {
            "total": len(SESSION_DB["preprocessed"]),
            "sample": SESSION_DB["preprocessed"][:10]
        }
    }
