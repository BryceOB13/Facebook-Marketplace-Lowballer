"""
Listing extraction from Facebook Marketplace pages.
"""

import re
import logging
from typing import List, Optional
from datetime import datetime

from src.models import Listing

logger = logging.getLogger(__name__)


class ListingExtractor:
    """Extract listing data from Facebook Marketplace HTML"""
    
    # JavaScript extraction script
    EXTRACTION_SCRIPT = """
    (function() {
        const listings = [];
        
        // Find all listing links
        const links = document.querySelectorAll('a[href*="/marketplace/item/"]');
        
        links.forEach(link => {
            try {
                // Extract ID from URL
                const match = link.href.match(/\\/marketplace\\/item\\/(\\d+)/);
                if (!match) return;
                
                const id = match[1];
                
                // Find parent container
                const container = link.closest('[role="article"], [data-testid*="marketplace"]') || link.parentElement;
                
                // Extract title (from link text or nearby heading)
                let title = link.textContent.trim();
                if (!title || title.length < 3) {
                    const heading = container.querySelector('h2, h3, [role="heading"]');
                    title = heading ? heading.textContent.trim() : '';
                }
                
                // Extract price (look for $ symbol)
                let price = '';
                const priceElements = container.querySelectorAll('span, div');
                for (const el of priceElements) {
                    const text = el.textContent.trim();
                    if (text.includes('$') && /\\$[\\d,]+/.test(text)) {
                        price = text.match(/\\$[\\d,]+/)[0];
                        break;
                    }
                }
                
                // Extract location
                let location = '';
                const locationElements = container.querySelectorAll('span[dir="auto"]');
                for (const el of locationElements) {
                    const text = el.textContent.trim();
                    if (text.includes(',') || text.includes('miles')) {
                        location = text;
                        break;
                    }
                }
                
                // Extract image URL
                let imageUrl = '';
                const img = container.querySelector('img');
                if (img) {
                    imageUrl = img.src || img.getAttribute('data-src') || '';
                }
                
                // Only add if we have minimum required data
                if (id && (title || price)) {
                    listings.push({
                        id: id,
                        title: title || 'Untitled',
                        price: price || 'Price not listed',
                        location: location || null,
                        image_url: imageUrl || null,
                        url: link.href,
                        seller_name: null
                    });
                }
            } catch (e) {
                console.error('Error extracting listing:', e);
            }
        });
        
        return listings;
    })()
    """
    
    def parse_price_value(self, price_str: str) -> Optional[int]:
        """
        Extract numeric value from price string.
        
        Args:
            price_str: Price string like "$1,200" or "$50"
            
        Returns:
            Integer price value or None
        """
        if not price_str:
            return None
        
        # Remove $ and commas, extract numbers
        match = re.search(r'[\d,]+', price_str.replace('$', ''))
        if match:
            try:
                return int(match.group().replace(',', ''))
            except ValueError:
                return None
        
        return None
    
    def create_listing_from_data(self, data: dict) -> Listing:
        """
        Create Listing object from extracted data.
        
        Args:
            data: Dictionary with listing data
            
        Returns:
            Listing object
        """
        price_value = self.parse_price_value(data.get('price', ''))
        
        return Listing(
            id=data['id'],
            title=data.get('title', 'Untitled'),
            price=data.get('price', 'Price not listed'),
            price_value=price_value,
            location=data.get('location'),
            image_url=data.get('image_url'),
            url=data['url'],
            seller_name=data.get('seller_name'),
            scraped_at=datetime.now(),
            created_at=datetime.now()
        )
    
    def extract_from_script_result(self, script_result: List[dict]) -> List[Listing]:
        """
        Convert JavaScript extraction result to Listing objects.
        
        Args:
            script_result: List of dicts from JavaScript extraction
            
        Returns:
            List of Listing objects
        """
        listings = []
        
        if not script_result:
            logger.warning("No listings found in script result")
            return listings
        
        for data in script_result:
            try:
                listing = self.create_listing_from_data(data)
                listings.append(listing)
            except Exception as e:
                logger.error(f"Failed to create listing from data: {e}")
                continue
        
        logger.info(f"Extracted {len(listings)} listings")
        return listings
