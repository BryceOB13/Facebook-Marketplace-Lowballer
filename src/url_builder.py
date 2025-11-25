"""
URL construction module for Facebook Marketplace searches.

This module provides functionality to build properly formatted and encoded
marketplace search URLs with query parameters.
"""

from urllib.parse import urlencode, quote_plus
from typing import Optional
from src.models import SearchCriteria


class MarketplaceURLBuilder:
    """Constructs Facebook Marketplace search URLs with encoded parameters.
    
    This class handles the construction of valid marketplace search URLs,
    ensuring proper encoding of query parameters and inclusion of filters.
    """
    
    BASE_URL = "https://www.facebook.com/marketplace/search"
    
    def build_search_url(
        self,
        query: str,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        location: Optional[str] = None
    ) -> str:
        """Construct marketplace search URL with query parameters.
        
        Builds a complete Facebook Marketplace search URL with properly encoded
        query parameters. Handles special characters in search terms and optional
        price/location filters.
        
        Args:
            query: Search keywords (will be URL-encoded)
            min_price: Minimum price filter (optional)
            max_price: Maximum price filter (optional)
            location: Location filter (optional)
            
        Returns:
            Complete marketplace search URL with encoded parameters
            
        Examples:
            >>> builder = MarketplaceURLBuilder()
            >>> builder.build_search_url("vintage guitar", max_price=1000)
            'https://www.facebook.com/marketplace/search?query=vintage+guitar&maxPrice=1000'
        """
        # Build parameters dictionary
        params = {'query': query}
        
        if min_price is not None:
            params['minPrice'] = str(min_price)
        
        if max_price is not None:
            params['maxPrice'] = str(max_price)
        
        if location:
            params['location'] = location
        
        # Use urlencode for proper URL encoding
        # quote_via=quote_plus converts spaces to + instead of %20
        encoded_params = urlencode(params, quote_via=quote_plus)
        
        return f"{self.BASE_URL}?{encoded_params}"
    
    def build_from_criteria(self, criteria: SearchCriteria) -> str:
        """Build URL from SearchCriteria object.
        
        Convenience method that accepts a SearchCriteria object and constructs
        the appropriate marketplace URL.
        
        Args:
            criteria: SearchCriteria object containing search parameters
            
        Returns:
            Complete marketplace search URL with encoded parameters
        """
        return self.build_search_url(
            query=criteria.query,
            min_price=criteria.min_price,
            max_price=criteria.max_price,
            location=criteria.location
        )
