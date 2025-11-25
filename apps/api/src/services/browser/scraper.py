"""
Facebook Marketplace scraper using Chrome MCP client.
"""

import asyncio
import logging
import os
from typing import List
from datetime import datetime, timedelta

from src.models import Listing
from .mcp_client import ChromeMCPClient
from .extractor import ListingExtractor

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
    
    async def search_listings(self, url: str) -> List[Listing]:
        """
        Search for listings at a given URL.
        
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
            # Navigate to search page
            success = await self.mcp_client.navigate(url)
            if not success:
                logger.error(f"Failed to navigate to {url}")
                return []
            
            # Check for login modal
            if await self._detect_login_required():
                logger.warning("Login required - please log into Facebook in Chrome")
                return []
            
            # Wait for initial content
            await asyncio.sleep(2)
            
            # Scroll to load more listings
            await self.mcp_client.scroll_page(iterations=3, delay_ms=2000)
            
            # Extract listings
            script_result = await self.mcp_client.execute_script(
                self.extractor.EXTRACTION_SCRIPT
            )
            
            if not script_result:
                logger.warning("No listings extracted")
                return []
            
            listings = self.extractor.extract_from_script_result(script_result)
            
            # Record request time
            self._record_request()
            
            # Human-like delay before next action
            import random
            delay = random.randint(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)
            
            return listings
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return []
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.
        
        Returns:
            True if request is allowed
        """
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Remove old requests
        self.request_times = [t for t in self.request_times if t > one_hour_ago]
        
        # Check limit
        return len(self.request_times) < self.max_pages_per_hour
    
    def _record_request(self):
        """Record a request for rate limiting"""
        self.request_times.append(datetime.now())
    
    async def _detect_login_required(self) -> bool:
        """
        Detect if Facebook is asking for login.
        
        Returns:
            True if login modal is present
        """
        script = """
        (function() {
            // Check for login modal or redirect
            const loginModal = document.querySelector('[role="dialog"]');
            const loginForm = document.querySelector('form[action*="login"]');
            const loginButton = document.querySelector('button[name="login"]');
            
            return !!(loginModal || loginForm || loginButton);
        })()
        """
        
        result = await self.mcp_client.execute_script(script)
        return result is True
