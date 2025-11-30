"""
Facebook Marketplace scraper using Chrome MCP client - FIXED VERSION
"""

import asyncio
import logging
import os
from typing import List
from datetime import datetime, timedelta

from src.models import Listing
from .mcp_client import ChromeMCPClient
from .extractor import ListingExtractor
from .scraper_fixed import SINGLE_LISTING_EXTRACTION_SCRIPT

logger = logging.getLogger(__name__)


class MarketplaceScraper:
    """
    Scrape Facebook Marketplace listings using Chrome automation.
    Includes rate limiting and anti-detection measures.
    """
    
    def __init__(self):
        chrome_port = os.getenv("CHROME_DEBUG_PORT", "9222")
        self.mcp_client = ChromeMCPClient(f"http://localhost:{chrome_port}")
        self.extractor = ListingExtractor()
        
        # Rate limiting
        self.max_pages_per_hour = int(os.getenv("MAX_PAGES_PER_HOUR", "10"))
        self.min_delay = int(os.getenv("MIN_DELAY_SECONDS", "3"))
        self.max_delay = int(os.getenv("MAX_DELAY_SECONDS", "7"))
        self.request_times: List[datetime] = []
    
    async def scrape_single_listing(self, url: str) -> dict:
        """
        Scrape a single listing page for detailed information.
        
        Args:
            url: Facebook Marketplace item URL
            
        Returns:
            Dict with listing details (title, price, description, condition, etc.)
        """
        try:
            # Navigate to listing page
            success = await self.mcp_client.navigate(url)
            if not success:
                logger.error(f"Failed to navigate to {url}")
                return None
            
            # Wait for page to load - Facebook loads content dynamically
            await asyncio.sleep(3)
            
            # Click somewhere on the page to ensure focus, then wait more
            await self.mcp_client.execute_script("document.body.click();")
            await asyncio.sleep(3)
            
            # Extract listing details using fixed extraction script
            result = await self.mcp_client.execute_script(SINGLE_LISTING_EXTRACTION_SCRIPT)
            
            if result:
                logger.info(f"Successfully scraped listing: {result.get('title', 'Unknown')}")
                logger.info(f"Scraped price: {result.get('price_value', 0)}")
                return result
            else:
                logger.warning("Failed to extract listing details")
                return None
                
        except Exception as e:
            logger.error(f"Failed to scrape single listing: {e}")
            return None
    
    async def search_listings(self, url: str) -> List[Listing]:
        """
        Search for listings at a given URL.
        
        Args:
            url: Facebook Marketplace search URL
            
        Returns:
            List of extracted listings
        """
        import random
        
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping request")
            return []
        
        try:
            # Navigate to search page
            success = await self.mcp_client.navigate(url)
            if not success:
                logger.error(f"Failed to navigate to {url}")
                return []
            
            # Wait for initial content to load
            await asyncio.sleep(3)
            
            # Scroll to load more listings
            await self.mcp_client.scroll_page(iterations=2, delay_ms=1500)
            
            # Wait a bit more after scrolling
            await asyncio.sleep(2)
            
            # Extract listings
            script_result = await self.mcp_client.execute_script(
                self.extractor.EXTRACTION_SCRIPT
            )
            
            if not script_result:
                logger.warning("No listings extracted - script returned None")
                return []
            
            if isinstance(script_result, list) and len(script_result) == 0:
                logger.warning("No listings extracted - empty list returned")
                return []
            
            listings = self.extractor.extract_from_script_result(script_result)
            logger.info(f"Successfully extracted {len(listings)} listings")
            
            # Record request time
            self._record_request()
            
            # Human-like delay before next action
            delay = random.randint(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)
            
            return listings
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return []
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        self.request_times = [t for t in self.request_times if t > one_hour_ago]
        return len(self.request_times) < self.max_pages_per_hour
    
    def _record_request(self):
        """Record a request for rate limiting"""
        self.request_times.append(datetime.now())
