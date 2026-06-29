import os
import json
import asyncio
from typing import List, Dict, Any
from backend.analysis.llm_client import LLMClient
from backend.analysis.prompts import get_analysis_prompt
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class BatchAnalyzer:
    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size
        self.client = LLMClient()
        self.preprocessed_file = os.path.join(os.getcwd(), "data", "preprocessed", "all_reviews.json")
        self.analyzed_file = os.path.join(os.getcwd(), "data", "analyzed", "reviews_analyzed.json")
        self.errors_dir = os.path.join(os.getcwd(), "data", "errors")
        
        os.makedirs(os.path.dirname(self.analyzed_file), exist_ok=True)
        os.makedirs(self.errors_dir, exist_ok=True)

    def _load_preprocessed(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.preprocessed_file):
            logger.error(f"[BatchAnalyzer] Preprocessed file not found: {self.preprocessed_file}")
            return []
        with open(self.preprocessed_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_analyzed_ids(self) -> set:
        """Returns a set of review_ids that have already been successfully analyzed."""
        if not os.path.exists(self.analyzed_file):
            return set()
        try:
            with open(self.analyzed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {r.get("review_id") for r in data}
        except json.JSONDecodeError:
            return set()

    def _save_batch(self, analyzed_batch: List[Dict[str, Any]]):
        """Appends a successful batch to the analyzed file."""
        existing = []
        if os.path.exists(self.analyzed_file):
            with open(self.analyzed_file, 'r', encoding='utf-8') as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        existing.extend(analyzed_batch)
        with open(self.analyzed_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
            
    def _save_error_batch(self, raw_batch: List[Dict[str, Any]], error_msg: str):
        """Saves a failed batch to the errors directory for later retry."""
        batch_id = raw_batch[0].get("review_id", "unknown")
        err_file = os.path.join(self.errors_dir, f"batch_{batch_id}_err.json")
        
        payload = {
            "error": str(error_msg),
            "batch": raw_batch
        }
        with open(err_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.warning(f"[BatchAnalyzer] Saved failed batch to {err_file}")

    async def _process_batch(self, batch: List[Dict[str, Any]], retry_count: int = 3):
        """Processes a single batch with retries."""
        prompt = get_analysis_prompt(batch)
        
        for attempt in range(1, retry_count + 1):
            try:
                response = await self.client.generate_json(prompt)
                
                # Verify format
                analyzed = response.get("reviews", [])
                if not isinstance(analyzed, list) or len(analyzed) == 0:
                    raise ValueError("LLM returned empty or malformed 'reviews' array.")
                    
                self._save_batch(analyzed)
                logger.info(f"[BatchAnalyzer] Successfully processed batch of {len(analyzed)} reviews.")
                return
                
            except Exception as e:
                logger.error(f"[BatchAnalyzer] Attempt {attempt} failed: {e}")
                if attempt == retry_count:
                    self._save_error_batch(batch, str(e))
                else:
                    await asyncio.sleep(2.0) # wait before retry

    async def run(self):
        """Main execution loop for batch analysis."""
        records = self._load_preprocessed()
        if not records:
            return
            
        analyzed_ids = self._load_analyzed_ids()
        
        # Filter out already analyzed records
        pending = [r for r in records if r.get("review_id") not in analyzed_ids]
        logger.info(f"[BatchAnalyzer] Found {len(records)} total records, {len(pending)} pending analysis.")
        
        if not pending:
            return
            
        # Chunk into batches
        batches = [pending[i:i + self.batch_size] for i in range(0, len(pending), self.batch_size)]
        
        for idx, batch in enumerate(batches):
            logger.info(f"[BatchAnalyzer] Processing batch {idx + 1}/{len(batches)}...")
            await self._process_batch(batch)
            
        logger.info("[BatchAnalyzer] Annotation run complete.")
