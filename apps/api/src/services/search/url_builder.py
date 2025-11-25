"""
Facebook Marketplace URL builder.
"""

from urllib.parse import urlencode, quote
from typing import Optional


class MarketplaceURLBuilder:
    """Build Facebook Marketplace search URLs"""
    
    BASE_URL = "https://www.facebook.com/marketplace"
    
    def build_search_url(
        self,
        query: str,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        location: Optional[str] = None,
        days_listed: Optional[int] = None,
        delivery_method: Optional[str] = None
    ) -> str:
        """
        Build a Facebook Marketplace search URL.
        
        Args:
            query: Search keywords
            min_price: Minimum price filter
            max_price: Maximum price filter
            location: Location filter
            days_listed: Days since listed (1, 7, 30)
            delivery_method: "local_pickup" or "shipping"
            
        Returns:
            Complete marketplace search URL
        """
        # Start with base search URL
        if location:
            # Location-specific search
            location_slug = location.lower().replace(' ', '-').replace(',', '')
            url = f"{self.BASE_URL}/{location_slug}/search"
        else:
            url = f"{self.BASE_URL}/search"
        
        # Build query parameters
        params = {"query": query}
        
        if min_price is not None:
            params["minPrice"] = str(min_price)
        
        if max_price is not None:
            params["maxPrice"] = str(max_price)
        
        if days_listed:
            params["daysSinceListed"] = str(days_listed)
        
        if delivery_method:
            params["deliveryMethod"] = delivery_method
        
        # Encode and append
        query_string = urlencode(params)
        return f"{url}?{query_string}"
    
    def build_item_url(self, item_id: str) -> str:
        """
        Build URL for a specific marketplace item.
        
        Args:
            item_id: Marketplace item ID
            
        Returns:
            Item detail URL
        """
        return f"{self.BASE_URL}/item/{item_id}/"
    
    def extract_item_id(self, url: str) -> Optional[str]:
        """
        Extract item ID from a marketplace URL.
        
        Args:
            url: Marketplace URL
            
        Returns:
            Item ID or None
        """
        import re
        match = re.search(r'/marketplace/item/(\d+)', url)
        return match.group(1) if match else None
