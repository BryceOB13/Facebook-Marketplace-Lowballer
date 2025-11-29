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
    
    # JavaScript extraction script - updated for current Facebook Marketplace structure
    EXTRACTION_SCRIPT = """
    (function() {
        const listings = [];
        
        // Facebook uses multiple possible selectors
        const links = document.querySelectorAll('a[href*="/marketplace/item/"]');
        
        console.log('Found ' + links.length + ' marketplace links');
        
        links.forEach((link, index) => {
            try {
                // Extract ID from URL
                const match = link.href.match(/\\/marketplace\\/item\\/(\\d+)/);
                if (!match) return;
                
                const id = match[1];
                
                // Find parent container
                let container = link.closest('div[class*="x1"]');
                if (!container) {
                    container = link.parentElement?.parentElement?.parentElement;
                }
                if (!container) {
                    container = link;
                }
                
                // Extract title from aria-label (most reliable)
                let title = link.getAttribute('aria-label') || '';
                title = title.trim();
                
                // If aria-label is too long or contains price, it's not the title
                if (title.includes('$') || title.length > 100) {
                    title = '';
                }
                
                // Fallback: get first span with meaningful text
                if (!title) {
                    const spans = container.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent.trim();
                        // Skip if it's a price, location, or too short
                        if (text.length > 5 && text.length < 100 && !text.includes('$') && !text.includes(',')) {
                            title = text;
                            break;
                        }
                    }
                }
                
                // Extract price
                let price = '';
                const priceMatch = container.textContent.match(/\\$[\\d,]+/);
                if (priceMatch) {
                    price = priceMatch[0];
                }
                
                // Extract location - look for city, state pattern
                let location = '';
                const allSpans = container.querySelectorAll('span');
                for (const span of allSpans) {
                    const text = span.textContent.trim();
                    // Look for "City, State" or "X miles away"
                    if ((text.match(/^[A-Z][a-z]+,\\s*[A-Z]{2}$/) || text.includes('miles')) && text !== title) {
                        location = text;
                        break;
                    }
                }
                
                // Extract image
                let imageUrl = '';
                const img = container.querySelector('img');
                if (img) {
                    imageUrl = img.src || img.getAttribute('data-src') || '';
                }
                
                // Only add if we have minimum required data
                if (id && title && title.length > 2) {
                    listings.push({
                        id: id,
                        title: title,
                        price: price || 'Price not listed',
                        location: location || null,
                        image_url: imageUrl || null,
                        url: link.href,
                        seller_name: null,
                        description: null
                    });
                }
            } catch (e) {
                console.error('Error extracting listing ' + index + ':', e);
            }
        });
        
        console.log('Extracted ' + listings.length + ' listings');
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
