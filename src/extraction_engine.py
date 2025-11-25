"""
Extraction engine for parsing Facebook Marketplace listings from DOM.

This module provides the ListingExtractor class that executes JavaScript
in the browser context to extract listing data from marketplace pages.
"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models import Listing


class ListingExtractor:
    """Extracts listing data from Facebook Marketplace pages.
    
    Uses JavaScript execution in the browser context to parse DOM elements
    and extract listing information using stable selectors (URL patterns
    and ARIA attributes) to avoid issues with obfuscated CSS classes.
    """
    
    def __init__(self):
        """Initialize the extraction engine."""
        pass
    
    async def extract_listings(self, execute_script_fn) -> List[Listing]:
        """Execute extraction JavaScript and parse results into Listing objects.
        
        Args:
            execute_script_fn: Async function that executes JavaScript in browser context
            
        Returns:
            List of extracted Listing objects
            
        Raises:
            ValueError: If extraction script returns invalid JSON
            RuntimeError: If script execution fails
        """
        # Get the extraction script
        script = self._get_extraction_script()
        
        # Execute the script in the browser context
        try:
            result = await execute_script_fn(script)
        except Exception as e:
            raise RuntimeError(f"Failed to execute extraction script: {e}")
        
        # Parse the JSON results
        listings = self._parse_extraction_results(result)
        
        return listings
    
    def _get_extraction_script(self) -> str:
        """Return JavaScript extraction function.
        
        Returns:
            JavaScript code as a string that extracts listing data from the DOM
        """
        # JavaScript extraction function that runs in the browser context
        script = """
() => {
  const listings = [];
  const seenIds = new Set();
  
  // Use stable URL pattern selector - most reliable approach
  const listingLinks = document.querySelectorAll('a[href*="/marketplace/item/"]');
  
  listingLinks.forEach(link => {
    try {
      // Navigate up to card container
      const card = link.closest('[data-pagelet]') || 
                   link.parentElement?.parentElement?.parentElement;
      if (!card) return;
      
      // Extract ID from URL using regex pattern (most reliable)
      const urlMatch = link.href.match(/\\/marketplace\\/item\\/(\\d+)/);
      const id = urlMatch ? urlMatch[1] : null;
      
      // Skip if no ID or duplicate
      if (!id || seenIds.has(id)) return;
      seenIds.add(id);
      
      // Extract price with currency symbol regex
      const priceEl = card.querySelector('span[dir="auto"]');
      const priceText = priceEl?.textContent || '';
      const priceMatch = priceText.match(/[\\$€£]\\s*\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?/);
      const price = priceMatch ? priceMatch[0] : null;
      
      // Extract title from span elements
      const spans = card.querySelectorAll('span');
      let title = null;
      for (const span of spans) {
        const text = span.textContent?.trim();
        // Look for text that's likely a title (reasonable length, not a price)
        if (text && text.length > 10 && text.length < 200 && 
            !text.match(/[\\$€£]/) && !text.match(/^\\d+$/)) {
          title = text;
          break;
        }
      }
      
      // Extract image URL
      const imgEl = card.querySelector('img');
      const imageUrl = imgEl?.src || null;
      
      // Extract location
      const allText = card.textContent;
      const locationMatch = allText.match(/(?:in\\s+)?([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*,\\s*[A-Z]{2})/);
      const location = locationMatch ? locationMatch[1] : null;
      
      // Only include if we have required fields (ID and at least title or price)
      if (id && (title || price)) {
        listings.push({
          id,
          title,
          price,
          location,
          imageUrl,
          url: link.href,
          scrapedAt: Date.now()
        });
      }
    } catch (error) {
      // Skip listings that cause errors during extraction
      console.error('Error extracting listing:', error);
    }
  });
  
  return JSON.stringify(listings, null, 2);
}
"""
        return script
    
    def _parse_extraction_results(self, json_str: str) -> List[Listing]:
        """Parse JSON results into Listing objects.
        
        Args:
            json_str: JSON string containing extracted listing data
            
        Returns:
            List of Listing objects
            
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from extraction script: {e}")
        
        if not isinstance(data, list):
            raise ValueError("Extraction results must be a list")
        
        listings = []
        seen_ids = set()
        
        for item in data:
            # Validate required fields
            if not isinstance(item, dict):
                continue
            
            listing_id = item.get('id')
            if not listing_id:
                continue
            
            # Duplicate filtering by listing ID
            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)
            
            # Must have at least title or price (Requirement 2.6)
            title = item.get('title')
            price = item.get('price')
            if not title and not price:
                continue
            
            # Parse scraped_at timestamp
            scraped_at_ms = item.get('scrapedAt')
            if isinstance(scraped_at_ms, (int, float)):
                scraped_at = datetime.fromtimestamp(scraped_at_ms / 1000.0)
            else:
                scraped_at = datetime.now()
            
            # Create Listing object
            listing = Listing(
                id=listing_id,
                title=title,
                price=price,
                location=item.get('location'),
                image_url=item.get('imageUrl'),
                url=item.get('url', ''),
                scraped_at=scraped_at
            )
            
            listings.append(listing)
        
        return listings
    
    @staticmethod
    def extract_id_from_url(url: str) -> Optional[str]:
        """Extract listing ID from marketplace URL.
        
        Uses regex pattern matching against the /marketplace/item/{ID}/ format.
        
        Args:
            url: Marketplace item URL
            
        Returns:
            Listing ID as string, or None if pattern doesn't match
        """
        match = re.search(r'/marketplace/item/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def parse_price_string(price_str: str) -> Optional[int]:
        """Parse price string to integer value.
        
        Handles various currency symbols ($, €, £) and comma-separated thousands.
        
        Args:
            price_str: Price string with currency symbol
            
        Returns:
            Integer price value, or None if parsing fails
        """
        if not price_str:
            return None
        
        # Match currency symbol followed by digits with optional commas
        match = re.search(r'[\$€£]?\s*(\d{1,3}(?:,\d{3})*|\d+)', price_str)
        if match:
            # Remove commas and convert to integer
            price_digits = match.group(1).replace(',', '')
            try:
                return int(price_digits)
            except ValueError:
                return None
        
        return None
