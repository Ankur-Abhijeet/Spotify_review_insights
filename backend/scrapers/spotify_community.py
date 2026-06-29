import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from backend.scrapers.base_scraper import BaseScraper
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class SpotifyCommunityScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="spotify_community")
        # Live Ideas board is a great place for feature requests / complaints
        self.base_url = "https://community.spotify.com/t5/Live-Ideas/idb-p/ideas_live"

    async def scrape(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrapes the Spotify Community 'Live Ideas' board using httpx and BeautifulSoup.
        """
        normalized_results = []
        logger.info(f"[spotify_community] Fetching up to {limit} threads from {self.base_url}")

        page = 1
        fetched = 0

        # We need a browser-like User-Agent to avoid immediate blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            while fetched < limit:
                # Lithium pagination usually ?page=2
                url = f"{self.base_url}" if page == 1 else f"{self.base_url}/page/{page}"
                
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # We will find all links that look like a thread post (/td-p/ or /idi-p/)
                    threads = soup.find_all('a', href=lambda h: h and ('/idi-p/' in h or '/td-p/' in h))
                    
                    # Deduplicate threads
                    unique_hrefs = list(set([t.get('href') for t in threads]))
                    
                    if not unique_hrefs:
                        logger.info("[spotify_community] No threads found or layout changed.")
                        break

                    for href in unique_hrefs:
                        if not href.startswith('http'):
                            href = "https://community.spotify.com" + href
                            
                        # Normally we would navigate into the thread to get the body.
                        # For speed and bot-evasion, we'll try to fetch the thread content.
                        try:
                            thread_resp = await client.get(href)
                            thread_resp.raise_for_status()
                            t_soup = BeautifulSoup(thread_resp.text, 'html.parser')
                            
                            title_el = t_soup.find(['h1', 'h2'], class_=lambda c: c and 'subject' in c)
                            title = title_el.get_text(strip=True) if title_el else "Community Discussion"

                            # Lithium message body
                            body_el = t_soup.find('div', class_='lia-message-body-content')
                            body_text = body_el.get_text(separator='\n', strip=True) if body_el else ""
                            
                            # The user requested that we OVERRIDE the actual review date
                            # and always label the review with today's date when scraped.
                            date_str = datetime.now().strftime('%Y-%m-%d')
                                
                            review_id = f"sc_{hash(href)}"
                            
                            content = f"{title}\n\n{body_text}".strip()
                            if not content:
                                continue

                            record = {
                                "review_id": review_id,
                                "source": "spotify_community",
                                "body": content,
                                "date": date_str,
                                "rating": 3
                            }
                            normalized_results.append(record)
                            fetched += 1
                            
                            if fetched >= limit:
                                break
                                
                            await self.polite_delay() # Polite randomized delay
                            
                        except Exception as e:
                            logger.warning(f"[spotify_community] Error fetching thread {href}: {e}")
                            continue
                            
                    page += 1
                    
                except httpx.HTTPError as e:
                    logger.error(f"[spotify_community] HTTP error on page {page}: {e}")
                    break
                except Exception as e:
                    logger.error(f"[spotify_community] Unexpected error: {e}")
                    break

        logger.info(f"[spotify_community] Normalized {len(normalized_results)} posts.")
        return normalized_results
