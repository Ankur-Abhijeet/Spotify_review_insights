import httpx
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from backend.scrapers.base_scraper import BaseScraper
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class AppStoreScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="app_store")
        # Spotify iOS App ID
        self.app_id = "324684580"
        self.base_url = "https://itunes.apple.com/us/rss/customerreviews"

    async def scrape(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrapes the Apple App Store for Spotify reviews using the iTunes RSS JSON API.
        Apple's RSS feed is limited to 10 pages of 50 reviews each (max 500).
        """
        normalized_results = []
        pages_to_fetch = min(10, (limit // 50) + (1 if limit % 50 > 0 else 0))
        
        logger.info(f"[app_store] Fetching up to {limit} reviews (approx {pages_to_fetch} pages) for App ID {self.app_id}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            for page in range(1, pages_to_fetch + 1):
                url = f"{self.base_url}/page={page}/id={self.app_id}/sortby=mostrecent/json"
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    
                    feed = data.get('feed', {})
                    entries = feed.get('entry', [])
                    
                    # If entries is a dict, wrap it in list (happens if only 1 review)
                    if isinstance(entries, dict):
                        entries = [entries]
                        
                    # First entry is sometimes the app metadata, not a review
                    for entry in entries:
                        if 'author' not in entry:
                            continue
                            
                        try:
                            # Parse rating
                            rating_str = entry.get('im:rating', {}).get('label', '3')
                            rating = int(rating_str)
                            
                            # The user requested that we OVERRIDE the actual review date
                            # and always label the review with today's date when scraped.
                            date_str = datetime.now().strftime('%Y-%m-%d')
                                
                            review_id = entry.get('id', {}).get('label', '')
                            # Fallback ID generation if missing
                            if not review_id:
                                review_id = f"as_{hash(entry.get('content', {}).get('label', ''))}"
                            else:
                                review_id = f"as_{review_id}"

                            content = entry.get('content', {}).get('label', '').strip()
                            
                            record = {
                                "review_id": review_id,
                                "source": "app_store",
                                "body": content,
                                "date": date_str,
                                "rating": rating
                            }
                            normalized_results.append(record)
                            
                            if len(normalized_results) >= limit:
                                break
                                
                        except Exception as e:
                            logger.warning(f"[app_store] Error normalizing an entry: {e}")
                            continue

                except httpx.HTTPError as e:
                    logger.error(f"[app_store] HTTP error on page {page}: {e}")
                    break
                except ValueError as e:
                    logger.error(f"[app_store] JSON parsing error on page {page}: {e}")
                    break
                    
                if len(normalized_results) >= limit:
                    break
                    
                # Use randomized polite delay to respect rate limits
                await self.polite_delay()

        logger.info(f"[app_store] Normalized {len(normalized_results)} reviews.")
        return normalized_results
