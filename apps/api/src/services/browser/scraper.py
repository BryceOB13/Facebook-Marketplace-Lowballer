"""
Facebook Marketplace scraper - OPTIMIZED VERSION
Uses Chrome MCP client with performance optimizations.

Optimizations:
- Smart scrolling with early termination
- Parallel detail page scraping
- Reduced wait times
- Better error handling
"""

import asyncio
import logging
import os
import random
from typing import List, Optional, Callable
from datetime import datetime, timedelta

from src.models import Listing
from .mcp_client import ChromeMCPClient
from .extractor import ListingExtractor
from .scraper_fixed import SINGLE_LISTING_EXTRACTION_SCRIPT

logger = logging.getLogger(__name__)


class MarketplaceScraper:
    """
    Optimized Facebook Marketplace scraper.
    Includes parallel processing and smart waiting.
    """
    
    def __init__(self):
        chrome_port = os.getenv("CHROME_DEBUG_PORT", "9222")
        self.mcp_client = ChromeMCPClient(f"http://localhost:{chrome_port}")
        self.extractor = ListingExtractor()
        
        # Rate limiting
        self.max_pages_per_hour = int(os.getenv("MAX_PAGES_PER_HOUR", "30"))
        self.min_delay = float(os.getenv("MIN_DELAY_SECONDS", "1"))
        self.max_delay = float(os.getenv("MAX_DELAY_SECONDS", "3"))
        self.request_times: List[datetime] = []
        
        # Parallel processing
        self.max_concurrent_pages = int(os.getenv("MAX_CONCURRENT_PAGES", "3"))
        self._semaphore = asyncio.Semaphore(self.max_concurrent_pages)
    
    async def scrape_single_listing(self, url: str) -> Optional[dict]:
        """
        Scrape a single listing page for detailed information.
        
        Args:
            url: Facebook Marketplace item URL
            
        Returns:
            Dict with listing details or None
        """
        try:
            # Navigate with DOM-ready wait (faster than full load)
            success = await self.mcp_client.navigate(url, wait_for="domcontentloaded")
            if not success:
                logger.error(f"Failed to navigate to {url}")
                return None
            
            # Wait for content to render
            await self.mcp_client.wait_for_network_idle(idle_time_ms=500, timeout_ms=3000)
            
            # Extract listing details
            result = await self.mcp_client.execute_script(SINGLE_LISTING_EXTRACTION_SCRIPT)
            
            if result:
                logger.info(f"Scraped listing: {result.get('title', 'Unknown')[:50]}")
                return result
            else:
                logger.warning("Failed to extract listing details")
                return None
                
        except Exception as e:
            logger.error(f"Failed to scrape single listing: {e}")
            return None
    
    async def search_listings(self, url: str) -> List[Listing]:
        """
        Search for listings at a given URL with optimized scrolling.
        
        Args:
            url: Facebook Marketplace search URL
            
        Returns:
            List of extracted listings
        """
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping request")
            return []
        
        try:
            # Navigate with DOM-ready wait
            success = await self.mcp_client.navigate(url, wait_for="domcontentloaded")
            if not success:
                logger.error(f"Failed to navigate to {url}")
                return []
            
            # Wait for marketplace items to appear
            await self.mcp_client.wait_for_selector(
                'a[href*="/marketplace/item/"]',
                timeout_ms=10000
            )
            
            # Smart scroll - stops early if target reached or no new items
            scroll_result = await self.mcp_client.scroll_until_target(
                target_count=30,
                max_iterations=3,
                selector='a[href*="/marketplace/item/"]'
            )
            
            logger.info(
                f"Scroll complete: {scroll_result['final_count']} items "
                f"in {scroll_result['iterations']} iterations "
                f"({scroll_result['stopped_reason']})"
            )
            
            # Extract listings
            script_result = await self.mcp_client.execute_script(
                self.extractor.EXTRACTION_SCRIPT
            )
            
            if not script_result:
                logger.warning("No listings extracted")
                return []
            
            listings = self.extractor.extract_from_script_result(script_result)
            logger.info(f"Extracted {len(listings)} listings")
            
            # Record request time
            self._record_request()
            
            # Short delay before next action
            delay = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)
            
            return listings
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return []

    
    async def scrape_listing_details_parallel(
        self,
        listing_urls: List[str],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[Optional[dict]]:
        """
        Scrape multiple listing detail pages in parallel.
        
        Args:
            listing_urls: List of marketplace item URLs
            on_progress: Optional callback(completed, total) for progress updates
        
        Returns:
            List of listing detail dicts (None for failed scrapes)
        """
        total = len(listing_urls)
        completed = 0
        results: List[Optional[dict]] = [None] * total
        
        async def scrape_with_semaphore(url: str, index: int):
            nonlocal completed
            async with self._semaphore:
                try:
                    # Apply rate limiting delay
                    delay = random.uniform(self.min_delay, self.max_delay)
                    await asyncio.sleep(delay)
                    
                    result = await self.scrape_single_listing(url)
                    results[index] = result
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")
                    results[index] = None
                finally:
                    completed += 1
                    if on_progress:
                        on_progress(completed, total)
        
        # Create all tasks
        tasks = [
            scrape_with_semaphore(url, i)
            for i, url in enumerate(listing_urls)
        ]
        
        # Execute with gather - don't fail on individual errors
        await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if r is not None)
        logger.info(f"Parallel scrape complete: {successful}/{total} successful")
        
        return results
    
    async def scrape_search_fast(
        self,
        search_url: str,
        max_detail_pages: int = 10
    ) -> dict:
        """
        Fast search flow: get listings, then parallel detail fetch.
        
        Returns:
            {
                'listings': List[Listing],
                'details': List[dict],
                'timing': {'search_ms': int, 'details_ms': int, 'total_ms': int}
            }
        """
        import time
        
        # Phase 1: Search and extract listing cards
        search_start = time.time()
        listings = await self.search_listings(search_url)
        search_time = (time.time() - search_start) * 1000
        
        # Phase 2: Parallel detail page scraping (optional)
        details = []
        details_time = 0
        
        if max_detail_pages > 0 and listings:
            details_start = time.time()
            detail_urls = [l.url for l in listings[:max_detail_pages]]
            details = await self.scrape_listing_details_parallel(detail_urls)
            details_time = (time.time() - details_start) * 1000
        
        return {
            'listings': listings,
            'details': details,
            'timing': {
                'search_ms': round(search_time),
                'details_ms': round(details_time),
                'total_ms': round(search_time + details_time)
            }
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        self.request_times = [t for t in self.request_times if t > one_hour_ago]
        return len(self.request_times) < self.max_pages_per_hour
    
    def _record_request(self):
        """Record a request for rate limiting."""
        self.request_times.append(datetime.now())
    
    async def check_browser_health(self) -> dict:
        """Check if Chrome browser is healthy and responsive."""
        return await self.mcp_client.check_health()
