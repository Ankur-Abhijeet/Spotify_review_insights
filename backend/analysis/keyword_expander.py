import os
import json
import httpx
from typing import List, Dict, Set
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class KeywordExpander:
    def __init__(self):
        # Fallback static dictionary if LLM is unavailable
        self.fallback_dict = {
            "discovery": ["explore", "new music", "recommendation", "fresh", "find"],
            "algorithm": ["shuffle", "mix", "radio", "predict", "auto"],
            "repetition": ["same songs", "repetitive", "stale", "loop", "boring"],
            "interface": ["ui", "ux", "menu", "layout", "nav", "app"]
        }

    async def expand(self, keywords: List[str]) -> Set[str]:
        """
        Expands a list of base keywords into a broader set of domain-specific synonyms
        and antonyms using a local LLM (Ollama) if available, else falls back to static map.
        """
        expanded = set(keywords)
        
        # Try Ollama expansion
        for keyword in keywords:
            llm_result = await self._try_llm_expansion(keyword)
            if llm_result:
                expanded.update(llm_result)
            else:
                # Fallback
                for k, v in self.fallback_dict.items():
                    if k.lower() in keyword.lower() or keyword.lower() in k.lower():
                        expanded.update(v)
                        
        logger.info(f"[Expander] Expanded {len(keywords)} keywords into {len(expanded)} terms: {expanded}")
        return expanded

    async def _try_llm_expansion(self, keyword: str) -> List[str]:
        prompt = f"""
        You are a linguistics expert for a music streaming service. 
        Given the target keyword "{keyword}", provide a comma-separated list of 10 
        synonyms, related jargon, or opposite concepts (antonyms) that a user might 
        say in a review when complaining or praising this aspect of Spotify.
        
        ONLY output the comma-separated words. No explanations.
        """
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3", # default local model
                        "prompt": prompt,
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    words = [w.strip() for w in response_text.split(',')]
                    return [w.lower() for w in words if w]
        except Exception as e:
            logger.debug(f"[Expander] LLM expansion failed for '{keyword}' (Ollama down?): {e}")
            
        return []
