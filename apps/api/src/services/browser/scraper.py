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
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        self.request_times = [t for t in self.request_times if t > one_hour_ago]
        return len(self.request_times) < self.max_pages_per_hour
    
    def _record_request(self):
        """Record a request for rate limiting"""
        self.request_times.append(datetime.now())
