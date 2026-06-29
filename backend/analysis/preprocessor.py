import os
import glob
import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from backend.utils.logger import get_logger
from backend.analysis.keyword_expander import KeywordExpander

logger = get_logger(__name__)

class Preprocessor:
    def __init__(self):
        self.raw_dir = os.path.join(os.getcwd(), "data", "raw")
        self.out_dir = os.path.join(os.getcwd(), "data", "preprocessed")
        self.expander = KeywordExpander()

    def load_raw_data(self) -> List[Dict[str, Any]]:
        """Loads all JSON files from the raw data directory structure."""
        all_records = []
        search_pattern = os.path.join(self.raw_dir, "**", "*.json")
        for filepath in glob.glob(search_pattern, recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_records.extend(data)
            except Exception as e:
                logger.error(f"[Preprocessor] Failed to load {filepath}: {e}")
                
        logger.info(f"[Preprocessor] Loaded {len(all_records)} total raw records.")
        return all_records

    def clean_text(self, text: str) -> str:
        """Removes HTML, decodes entities, and collapses whitespace."""
        if not text: return ""
        # Remove HTML
        soup = BeautifulSoup(text, "html.parser")
        clean = soup.get_text(separator=' ')
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def deduplicate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Exact ID and basic prefix deduplication."""
        seen_ids = set()
        seen_prefixes = set()
        deduped = []
        
        for r in records:
            rid = r.get('review_id')
            if rid in seen_ids:
                continue
                
            body = str(r.get('body', ''))
            # 50 char prefix for basic fuzzy dedup
            prefix = body[:50].lower()
            
            if prefix in seen_prefixes and len(body) > 20:
                continue
                
            seen_ids.add(rid)
            seen_prefixes.add(prefix)
            deduped.append(r)
            
        logger.info(f"[Preprocessor] Deduplicated from {len(records)} to {len(deduped)} records.")
        return deduped

    def calculate_density(self, text: str, expanded_keywords: set) -> float:
        """Calculates keyword density score."""
        if not expanded_keywords:
            return 1.0 # If no keywords provided, everything gets a passing score
            
        words = re.findall(r'\b\w+\b', text.lower())
        if not words: return 0.0
        
        matches = sum(1 for w in words if w in expanded_keywords)
        
        # We also want to match multi-word phrases from expansion (e.g. "new music")
        # So we do a substring check for phrases
        phrases = [k for k in expanded_keywords if ' ' in k]
        text_lower = text.lower()
        phrase_matches = sum(1 for p in phrases if p in text_lower)
        
        total_matches = matches + (phrase_matches * 2) # weight phrases a bit higher
        return total_matches / len(words)

    async def process_records(self, raw_records: List[Dict[str, Any]], keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Executes the preprocessing pipeline on in-memory records."""
        # 1. Dedup
        records = self.deduplicate(raw_records)
        
        # 2. Clean & Filter
        cleaned_records = []
        for r in records:
            body = self.clean_text(r.get('body', ''))
            r['body'] = body
            
            if len(body) < 20:
                continue
                
            if not re.search(r'[a-zA-Z]', body):
                continue
                
            cleaned_records.append(r)
            
        # 3. Semantic Expansion & Density Sorting
        if not keywords:
            keywords = [
                "discovery", "algorithm", "recommendation", "explore",
                "repetition", "repetitive", "mix", "shuffle",
                "curation", "playlist", "new music", "stale"
            ]

        expanded_set = await self.expander.expand(keywords)
        for r in cleaned_records:
            r['density_score'] = self.calculate_density(r['body'], expanded_set)
            
        cleaned_records = [r for r in cleaned_records if r.get('density_score', 0) > 0]
        cleaned_records.sort(key=lambda x: x.get('density_score', 0), reverse=True)
        
        return cleaned_records
