import os
import json
import random
import asyncio
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class BaseScraper(ABC):
    """
    Abstract base class for all data source scrapers.
    Enforces the unified raw data schema and provides utility methods for saving data.
    """

    def __init__(self, source_name: str, min_delay: float = 3.0, max_delay: float = 7.0):
        self.source_name = source_name
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def polite_delay(self):
        """Introduces a random asynchronous delay to avoid rate limits and bot detection."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"[{self.source_name}] Sleeping for {delay:.2f}s...")
        await asyncio.sleep(delay)

    @abstractmethod
    async def scrape(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Main method to execute the scrape. Must be implemented by subclasses.
        Returns a list of dictionaries matching the raw schema.
        """
        pass

    def validate_record(self, record: Dict[str, Any]) -> bool:
        """
        Validates that a scraped record matches the required raw schema.
        Required fields: review_id, source, body, date
        """
        required_fields = ['review_id', 'source', 'body', 'date']
        for field in required_fields:
            if field not in record:
                logger.warning(f"[{self.source_name}] Record missing required field '{field}'")
                return False
            
            # Additional check: body should not be completely empty
            if field == 'body' and not str(record['body']).strip():
                logger.warning(f"[{self.source_name}] Record has empty body")
                return False

        # Ensure rating exists (even if it's a default for non-star systems)
        if 'rating' not in record:
            record['rating'] = 3

        # Add scraped timestamp if missing
        if 'scraped_at' not in record:
            record['scraped_at'] = datetime.now().isoformat()
            
        return True

