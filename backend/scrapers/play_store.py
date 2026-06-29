import asyncio
from datetime import datetime
from typing import List, Dict, Any
from google_play_scraper import reviews, Sort
from backend.scrapers.base_scraper import BaseScraper
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class PlayStoreScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="play_store")
        self.app_id = "com.spotify.music"

    def _scrape_sync(self, limit: int) -> List[Dict[str, Any]]:
        """Synchronous wrapper around the google-play-scraper library"""
        logger.info(f"[play_store] Fetching up to {limit} recent reviews for {self.app_id}")
        
        try:
            result, _ = reviews(
                self.app_id,
                lang='en', # default language
                country='us', # default country
                sort=Sort.NEWEST,
                count=limit
            )
            return result
        except Exception as e:
            logger.error(f"[play_store] Failed to fetch reviews: {str(e)}")
            return []

    async def scrape(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrapes the Google Play Store for Spotify reviews.
        Uses asyncio.to_thread to run the synchronous scraper in the background.
        """
        # Introduce a polite delay before initiating the synchronous 3rd party scraper
        await self.polite_delay()
        raw_results = await asyncio.to_thread(self._scrape_sync, limit)
        
        normalized_results = []
        for r in raw_results:
            try:
                # Play Store format: 
                # {
                #   'reviewId': '...', 
                #   'content': '...', 
                #   'score': 5, 
                #   'at': datetime.datetime(...)
                # }
                
                # The user requested that we OVERRIDE the actual review date
                # and always label the review with today's date when scraped.
                date_str = datetime.now().strftime('%Y-%m-%d')

                record = {
                    "review_id": f"ps_{r.get('reviewId')}",
                    "source": "play_store",
                    "body": r.get('content', '').strip(),
                    "date": date_str,
                    "rating": r.get('score', 3)
                }
                
                normalized_results.append(record)
                
            except Exception as e:
                logger.warning(f"[play_store] Error normalizing record: {e}")
                continue
                
        # The library sometimes returns slightly fewer or more, we cap it exactly if needed
        normalized_results = normalized_results[:limit]
        
        logger.info(f"[play_store] Normalized {len(normalized_results)} reviews.")
        return normalized_results
