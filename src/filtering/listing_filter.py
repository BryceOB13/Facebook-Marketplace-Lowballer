"""
Listing filter implementation for marketplace results.

This module provides filtering capabilities for marketplace listings based on
price ranges and location patterns.
"""

from typing import List, Optional
import re
from src.models import Listing


class ListingFilter:
    """Filters marketplace listings based on various criteria.
    
    This class provides methods to filter listings by price range and location,
    excluding listings that don't meet the specified criteria.
    """
    
    def filter_by_price(
        self,
        listings: List[Listing],
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> List[Listing]:
        """Filter listings by price range.
        
        Filters listings to include only those within the specified price range.
        Listings without extractable prices are excluded from results.
        
        Args:
            listings: List of listings to filter
            min_price: Minimum price (inclusive), None for no minimum
            max_price: Maximum price (inclusive), None for no maximum
            
        Returns:
            List of listings that meet the price criteria
        """
        filtered = []
        
        for listing in listings:
            price_value = self._parse_price(listing.price)
            
            # Exclude listings without extractable prices
            if price_value is None:
                continue
            
            # Apply minimum price filter
            if min_price is not None and price_value < min_price:
                continue
            
            # Apply maximum price filter
            if max_price is not None and price_value > max_price:
                continue
            
            filtered.append(listing)
        
        return filtered
    
    def filter_by_location(
        self,
        listings: List[Listing],
        location_pattern: str
    ) -> List[Listing]:
        """Filter listings by location pattern matching.
        
        Filters listings to include only those whose location matches the
        specified pattern (case-insensitive substring match).
        
        Args:
            listings: List of listings to filter
            location_pattern: Location pattern to match (case-insensitive)
            
        Returns:
            List of listings with matching locations
        """
        filtered = []
        pattern_lower = location_pattern.lower()
        
        for listing in listings:
            if listing.location and pattern_lower in listing.location.lower():
                filtered.append(listing)
        
        return filtered
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[int]:
        """Parse price string to extract integer value.
        
        Extracts numeric value from price strings containing currency symbols
        and comma separators. Handles formats like "$1,234", "€500", "£99".
        
        Args:
            price_str: Price string to parse
            
        Returns:
            Integer price value, or None if price cannot be parsed
        """
        if not price_str:
            return None
        
        # Remove currency symbols and commas, extract digits
        # Pattern matches currency symbols followed by digits with optional commas
        match = re.search(r'[\$€£]?\s*(\d{1,3}(?:,\d{3})*|\d+)', price_str)
        if match:
            # Remove commas and convert to integer
            price_str_clean = match.group(1).replace(',', '')
            try:
                return int(price_str_clean)
            except ValueError:
                return None
        
        return None
