"""
Data models for the Marketplace Deal Scout.

This module defines the core data structures used throughout the application.
"""

from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
import re


@dataclass
class Listing:
    """Represents a marketplace listing.
    
    Attributes:
        id: Unique listing identifier extracted from URL
        title: Listing title/description
        price: Raw price string with currency symbol
        location: Geographic location of the listing
        image_url: URL to the listing's primary image
        url: Full marketplace item URL
        scraped_at: Timestamp when the listing was scraped
    """
    id: str
    title: Optional[str]
    price: Optional[str]
    location: Optional[str]
    image_url: Optional[str]
    url: str
    scraped_at: datetime
    
    def to_dict(self) -> dict:
        """Convert listing to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation with datetime converted to ISO format
        """
        data = asdict(self)
        # Convert datetime to ISO format string for JSON serialization
        data['scraped_at'] = self.scraped_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Listing':
        """Create Listing instance from dictionary.
        
        Args:
            data: Dictionary containing listing data
            
        Returns:
            Listing instance
        """
        # Convert ISO format string back to datetime
        if isinstance(data.get('scraped_at'), str):
            data = data.copy()
            data['scraped_at'] = datetime.fromisoformat(data['scraped_at'])
        return cls(**data)
    
    def get_price_value(self) -> Optional[int]:
        """Parse price string to integer value.
        
        Extracts numeric value from price strings containing currency symbols
        and comma separators. Handles formats like "$1,234", "€500", "£99".
        
        Returns:
            Integer price value, or None if price cannot be parsed
        """
        if not self.price:
            return None
        
        # Remove currency symbols and commas, extract digits
        # Pattern matches currency symbols followed by digits with optional commas
        match = re.search(r'[\$€£]?\s*(\d{1,3}(?:,\d{3})*|\d+)', self.price)
        if match:
            # Remove commas and convert to integer
            price_str = match.group(1).replace(',', '')
            try:
                return int(price_str)
            except ValueError:
                return None
        
        return None


@dataclass
class SearchCriteria:
    """User search parameters for marketplace queries.
    
    Attributes:
        query: Search keywords
        min_price: Minimum price filter (optional)
        max_price: Maximum price filter (optional)
        location: Location filter (optional)
        category: Category filter (optional)
    """
    query: str
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    location: Optional[str] = None
    category: Optional[str] = None
    
    def to_url_params(self) -> dict:
        """Convert search criteria to URL query parameters.
        
        Returns:
            Dictionary of query parameters with non-None values
        """
        params = {'query': self.query}
        
        if self.min_price is not None:
            params['minPrice'] = str(self.min_price)
        
        if self.max_price is not None:
            params['maxPrice'] = str(self.max_price)
        
        if self.location:
            params['location'] = self.location
        
        if self.category:
            params['category'] = self.category
        
        return params


@dataclass
class DealAlert:
    """Represents a deal matching user criteria.
    
    Attributes:
        listing: The marketplace listing
        is_new: Whether this listing is newly discovered (not in memory)
        price_changed: Whether the price has changed since last seen
        old_price: Previous price if price_changed is True
        match_reason: Explanation of why this is a good deal
    """
    listing: Listing
    is_new: bool
    price_changed: bool
    old_price: Optional[str] = None
    match_reason: str = ""
