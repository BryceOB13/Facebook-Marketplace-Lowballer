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
            
            # Wait for initial content to load
            await asyncio.sleep(3)
            
            # Scroll to load more listings
            await self.mcp_client.scroll_page(iterations=3, delay_ms=2000)
            
            # Wait a bit more after scrolling
            await asyncio.sleep(2)
            
            # Debug: check page content
            page_check = await self.mcp_client.execute_script("""
                (function() {
                    return {
                        title: document.title,
                        hasMarketplaceLinks: document.querySelectorAll('a[href*="/marketplace/item/"]').length,
                        bodyLength: document.body.innerText.length
                    };
                })()
            """)
            logger.info(f"Page check: {page_check}")
            
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
            
            # Extract listing details - improved for Facebook's actual DOM
            script = """
            (function() {
                try {
                    // Get the full page text - we'll parse it carefully
                    const bodyText = document.body.innerText;
                    
                    // Debug: log first 1000 chars to see what we're working with
                    console.log('Page text preview:', bodyText.substring(0, 1000));
                    
                    // Extract title - usually the first h1 or large heading
                    let title = '';
                    const h1 = document.querySelector('h1');
                    if (h1) {
                        title = h1.innerText.trim();
                    }
                    
                    // Extract price - look near the title element
                    let priceText = '';
                    let price = 0;
                    
                    // Method 1: Find h1 and look at nearby elements for price
                    const h1El = document.querySelector('h1');
                    if (h1El) {
                        // Get the parent container and look for price there
                        let container = h1El.parentElement;
                        for (let i = 0; i < 5 && container; i++) {
                            const containerText = container.innerText;
                            const priceMatch = containerText.match(/\\$([\\d,]+)/);
                            if (priceMatch) {
                                priceText = '$' + priceMatch[1];
                                price = parseFloat(priceMatch[1].replace(/,/g, ''));
                                break;
                            }
                            container = container.parentElement;
                        }
                    }
                    
                    // Method 2: Look for spans with exact price format
                    if (price === 0) {
                        const allSpans = document.querySelectorAll('span');
                        for (const span of allSpans) {
                            const text = span.innerText.trim();
                            if (/^\\$[\\d,]+$/.test(text)) {
                                const numVal = parseFloat(text.replace(/[$,]/g, ''));
                                if (numVal > 0 && numVal < 100000) {
                                    priceText = text;
                                    price = numVal;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Extract description - look for longer text blocks
                    let description = '';
                    const allDivs = document.querySelectorAll('div');
                    for (const div of allDivs) {
                        const text = div.innerText.trim();
                        // Description is usually a longer text block
                        if (text.length > 50 && text.length < 2000 && 
                            !text.includes('Message') && !text.includes('Share')) {
                            // Check if it looks like a description
                            if (text.toLowerCase().includes('condition') || 
                                text.toLowerCase().includes('working') ||
                                text.toLowerCase().includes('used') ||
                                text.toLowerCase().includes('new')) {
                                description = text;
                                break;
                            }
                        }
                    }
                    
                    // Extract condition from the details section
                    let condition = 'USED';
                    if (bodyText.includes('Used - like new')) condition = 'Used - like new';
                    else if (bodyText.includes('Used - good')) condition = 'Used - good';
                    else if (bodyText.includes('Used - fair')) condition = 'Used - fair';
                    else if (bodyText.includes('New')) condition = 'New';
                    
                    // Extract location - look for city, state pattern
                    let location = '';
                    const locationMatch = bodyText.match(/in ([A-Za-z\\s]+, [A-Z]{2})/);
                    if (locationMatch) {
                        location = locationMatch[1];
                    } else {
                        // Try to find "Location is approximate" section
                        const locMatch = bodyText.match(/([A-Za-z\\s]+, [A-Z]{2})\\s*Location is approximate/);
                        if (locMatch) {
                            location = locMatch[1];
                        }
                    }
                    
                    // Extract image
                    let image = '';
                    const imgEl = document.querySelector('img[src*="scontent"]');
                    if (imgEl) {
                        image = imgEl.src;
                    }
                    
                    // Find all prices on the page for debugging
                    const allPrices = bodyText.match(/\\$[\\d,]+/g) || [];
                    
                    return {
                        title: title,
                        price: priceText,
                        price_value: price,
                        description: description,
                        condition: condition,
                        location: location,
                        seller_name: '',
                        image_url: image,
                        url: window.location.href,
                        debug_prices: allPrices.slice(0, 10),
                        debug_first_1000: bodyText.substring(0, 1000)
                    };
                } catch (e) {
                    return { error: e.toString() };
                }
            })()
            """
            
            result = await self.mcp_client.execute_script(script)
            
            if result:
                logger.info(f"Successfully scraped listing: {result.get('title', 'Unknown')}")
                logger.info(f"Scraped price: {result.get('price_value', 0)} - All prices found: {result.get('debug_prices', [])}")
                logger.info(f"First 500 chars: {result.get('debug_first_1000', '')[:500]}")
                return result
            else:
                logger.warning("Failed to extract listing details")
                return None
                
        except Exception as e:
            logger.error(f"Failed to scrape single listing: {e}")
            return None
