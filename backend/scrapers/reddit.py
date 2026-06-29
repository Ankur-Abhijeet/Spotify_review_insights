import httpx
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from backend.scrapers.base_scraper import BaseScraper
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class RedditScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="reddit")
        self.base_url = "https://api.pullpush.io/reddit/search/submission/"
        # Keywords highly relevant to Spotify discovery
        self.query = "discover|algorithm|recommendation|playlist|explore"
        self.subreddit = "spotify"

    async def scrape(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrapes Reddit (r/spotify) using the PullPush API for submissions.
        Returns threads related to discovery and recommendations.
        """
        normalized_results = []
        logger.info(f"[reddit] Fetching up to {limit} submissions from r/{self.subreddit}")

        # PullPush supports up to 100 per request.
        batch_size = min(limit, 100)
        fetched = 0
        before = None

        async with httpx.AsyncClient(timeout=20.0) as client:
            while fetched < limit:
                params = {
                    "subreddit": self.subreddit,
                    "q": self.query,
                    "size": batch_size,
                    "sort": "desc"
                }
                if before:
                    params["before"] = before

                try:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    submissions = data.get('data', [])
                    if not submissions:
                        logger.info("[reddit] No more submissions found.")
                        break

                    for sub in submissions:
                        try:
                            # Submissions might have selftext and title
                            title = sub.get('title', '').strip()
                            selftext = sub.get('selftext', '').strip()
                            
                            # Skip removed/deleted posts
                            if selftext in ['[removed]', '[deleted]']:
                                selftext = ""
                                
                            body = f"{title}\n\n{selftext}".strip()
                            
                            if not body:
                                continue

                            # The user requested that we OVERRIDE the actual review date
                            # and always label the review with today's date when scraped.
                            from datetime import datetime
                            date_str = datetime.now().strftime('%Y-%m-%d')
                            
                            review_id = f"rd_{sub.get('id')}"

                            record = {
                                "review_id": review_id,
                                "source": "reddit",
                                "body": body,
                                "date": date_str,
                                "rating": 3 # Default rating for non-star platforms
                            }
                            normalized_results.append(record)
                            fetched += 1
                            
                            if fetched >= limit:
                                break
                                
                        except Exception as e:
                            logger.warning(f"[reddit] Error normalizing an entry: {e}")
                            continue

                    # Update 'before' to the oldest post's timestamp for pagination
                    before = submissions[-1].get('created_utc')

                    if fetched >= limit:
                        break

                    # Randomized polite delay
                    await self.polite_delay()

                except httpx.HTTPError as e:
                    logger.error(f"[reddit] HTTP error: {e}")
                    break
                except Exception as e:
                    logger.error(f"[reddit] Unexpected error: {e}")
                    break

        logger.info(f"[reddit] Normalized {len(normalized_results)} submissions.")
        return normalized_results
