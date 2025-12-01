"""
Listing extraction from Facebook Marketplace pages - OPTIMIZED VERSION
Single DOM query for all listings with metadata tracking.
"""

import re
import logging
from typing import List, Optional
from datetime import datetime

from src.models import Listing

logger = logging.getLogger(__name__)


class ListingExtractor:
    """Optimized listing extraction with single DOM query."""
    
    # Optimized extraction script - single pass, returns JSON with metadata
    EXTRACTION_SCRIPT = r"""
    (function() {
        const startTime = performance.now();
        const listings = [];
        const seenIds = new Set();
        
        // Get all marketplace item links in single query
        const links = document.querySelectorAll('a[href*="/marketplace/item/"]');
        
        links.forEach((link, index) => {
            try {
                // Extract ID from URL
                const match = link.href.match(/\/marketplace\/item\/(\d+)/);
                if (!match || seenIds.has(match[1])) return;
                seenIds.add(match[1]);
                
                const id = match[1];
                
                // Find parent container - traverse up max 5 levels
                let container = link;
                for (let i = 0; i < 5 && container.parentElement; i++) {
                    container = container.parentElement;
                    if (container.querySelector('img') && container.textContent.includes('$')) break;
                }
                
                // Extract title from aria-label first (most reliable)
                let title = link.getAttribute('aria-label') || '';
                title = title.trim();
                
                // If aria-label contains price or is too long, clear it
                if (title.includes('$') || title.length > 100) {
                    title = '';
                }
                
                // Fallback: find best span text
                if (!title) {
                    const spans = container.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent.trim();
                        
                        // Skip unwanted patterns
                        const isTimeIndicator = /^\d+[hdwm]/.test(text);
                        const isBadge = text.includes('Price dropped') || 
                                       text.includes('Pending') || 
                                       text.includes('Sold') || 
                                       text.includes('Free') ||
                                       text.includes('·');
                        const isPrice = text.includes('$');
                        const isLocation = text.includes(',') && text.length < 25;
                        
                        if (text.length > 5 && text.length < 100 && 
                            !isPrice && !isLocation && !isTimeIndicator && !isBadge) {
                            title = text;
                            break;
                        }
                    }
                }
                
                // Extract price - look for standalone price patterns
                let price = '';
                const allSpans = container.querySelectorAll('span');
                for (const span of allSpans) {
                    const text = span.textContent.trim();
                    // Match standalone price like "$2,800" but not "$2,8002000"
                    if (/^\$[\d,]+$/.test(text)) {
                        price = text;
                        break;
                    }
                }
                
                // Fallback: regex from container text
                if (!price) {
                    const priceMatches = container.textContent.match(/\$[\d,]+/g);
                    if (priceMatches && priceMatches.length > 0) {
                        price = priceMatches[0];
                    }
                }
                
                // Extract location
                let location = '';
                for (const span of allSpans) {
                    const text = span.textContent.trim();
                    if ((text.match(/^[A-Z][a-z]+,\s*[A-Z]{2}$/) || text.includes('miles')) && text !== title) {
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
                // Skip failed extractions silently
            }
        });
        
        return listings;
    })()
    """

    def parse_price_value(self, price_str: str) -> Optional[int]:
        """Extract numeric value from price string, handling year contamination."""
        if not price_str:
            return None
        
        # Remove $ and commas
        clean = price_str.replace('$', '').replace(',', '')
        
        # Check if the number ends with what looks like a year (1900-2099)
        if len(clean) > 4 and clean.isdigit():
            last_four = clean[-4:]
            year = int(last_four)
            if 1900 <= year <= 2099:
                # Remove the year from the end
                clean = clean[:-4]
        
        # Extract the price
        match = re.search(r'\d+', clean)
        if match:
            try:
                return int(match.group())
            except ValueError:
                return None
        return None
    
    def clean_price_string(self, price_str: str) -> str:
        """Clean price string by removing year contamination."""
        if not price_str or price_str == 'Price not listed':
            return price_str
        
        # Extract just the price part
        match = re.match(r'(\$[\d,]+)', price_str)
        if match:
            price_part = match.group(1)
            clean_num = price_part.replace('$', '').replace(',', '')
            
            # Check if there's a year stuck to it (e.g., $2,8002000 -> $2,800)
            if len(clean_num) > 4 and clean_num.isdigit():
                last_four = clean_num[-4:]
                year = int(last_four)
                if 1900 <= year <= 2099:
                    # Remove year and reformat
                    clean_num = clean_num[:-4]
                    if clean_num:
                        return f"${int(clean_num):,}"
            return price_part
        return price_str
    
    def create_listing_from_data(self, data: dict) -> Listing:
        """Create Listing object from extracted data."""
        raw_price = data.get('price', 'Price not listed')
        clean_price = self.clean_price_string(raw_price)
        price_value = self.parse_price_value(raw_price)
        
        return Listing(
            id=data['id'],
            title=data.get('title', 'Untitled'),
            price=clean_price,
            price_value=price_value,
            location=data.get('location'),
            image_url=data.get('image_url'),
            url=data['url'],
            seller_name=data.get('seller_name'),
            scraped_at=datetime.now(),
            created_at=datetime.now()
        )
    
    def extract_from_script_result(self, script_result: List[dict]) -> List[Listing]:
        """Convert JavaScript extraction result to Listing objects."""
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
