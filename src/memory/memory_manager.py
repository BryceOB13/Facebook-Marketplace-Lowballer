"""
Memory management for Deal Scout.

This module handles persistent storage and retrieval of listing history
using the mem0_memory MCP tool for cross-session deal tracking.
"""

from typing import Callable, Optional, Tuple, List, Dict, Any
from datetime import datetime
from src.models import Listing


class DealMemoryManager:
    """Manages persistent storage and retrieval of listing history.
    
    Uses mem0_memory MCP tool to store and retrieve listings across sessions,
    enabling deal tracking and price change detection.
    """
    
    def __init__(
        self,
        user_id: str = "deal_scout",
        mem0_tool: Callable = None
    ):
        """Initialize memory manager with MCP tool access.
        
        Args:
            user_id: User identifier for memory storage
            mem0_tool: Callable mem0_memory MCP tool for storage operations
        """
        self.user_id = user_id
        self.mem0_tool = mem0_tool
    
    async def store_listing(
        self,
        listing: Listing,
        category: str
    ) -> bool:
        """Store listing in persistent memory.
        
        Stores listing details with metadata for later retrieval and comparison.
        
        Args:
            listing: Listing object to store
            category: Category/search term for the listing
            
        Returns:
            True if storage successful, False otherwise
            
        **Validates: Requirements 4.1, 4.2**
        """
        if not self.mem0_tool:
            return False
        
        try:
            # Format content as specified in requirements
            location_str = listing.location or "Unknown location"
            content = f"Found {listing.title}, {listing.price}, {location_str} - listing ID {listing.id}"
            
            # Determine price range for metadata
            price_value = listing.get_price_value()
            if price_value:
                # Create a price range string (e.g., "500-1000")
                # For simplicity, use the price as both min and max
                price_range = f"{price_value}-{price_value}"
            else:
                price_range = "unknown"
            
            # Prepare metadata with all required fields
            metadata = {
                "category": category,
                "price_range": price_range,
                "listing_id": listing.id,
                "stored_at": datetime.now().isoformat()
            }
            
            # Call mem0_memory tool to store
            result = await self.mem0_tool(
                content=content,
                user_id=self.user_id,
                metadata=metadata
            )
            
            return result is not None
        except Exception:
            return False
    
    async def retrieve_listings(
        self,
        query: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve previously stored listings matching query.
        
        Searches memory for listings matching the query and optional category.
        
        Args:
            query: Search query string
            category: Optional category filter
            
        Returns:
            List of stored listing records
            
        **Validates: Requirements 4.3**
        """
        if not self.mem0_tool:
            return []
        
        try:
            # Build search query with category if provided
            search_query = query
            if category:
                search_query = f"{query} category:{category}"
            
            # Call mem0_memory tool to search
            results = await self.mem0_tool(
                query=search_query,
                user_id=self.user_id
            )
            
            return results if results else []
        except Exception:
            return []
    
    async def check_if_new(
        self,
        listing_id: str
    ) -> bool:
        """Check if listing ID exists in memory.
        
        Searches memory for the listing ID to determine if it's a new listing.
        
        Args:
            listing_id: Listing ID to check
            
        Returns:
            True if listing is new (not in memory), False if already stored
            
        **Validates: Requirements 4.4**
        """
        if not self.mem0_tool:
            return True  # Assume new if no memory tool available
        
        try:
            # Search for listing ID in memory
            search_query = f"listing ID {listing_id}"
            results = await self.mem0_tool(
                query=search_query,
                user_id=self.user_id
            )
            
            # If results found, listing is not new
            return not results or len(results) == 0
        except Exception:
            return True  # Assume new on error
    
    async def detect_price_change(
        self,
        listing_id: str,
        current_price: str
    ) -> Optional[Tuple[str, str]]:
        """Detect if listing price has changed since last seen.
        
        Compares current price against stored price for the listing ID.
        
        Args:
            listing_id: Listing ID to check
            current_price: Current price string
            
        Returns:
            Tuple of (old_price, new_price) if price changed, None otherwise
            
        **Validates: Requirements 4.5**
        """
        if not self.mem0_tool:
            return None
        
        try:
            # Search for listing ID in memory
            search_query = f"listing ID {listing_id}"
            results = await self.mem0_tool(
                query=search_query,
                user_id=self.user_id
            )
            
            if not results or len(results) == 0:
                return None
            
            # Extract price from stored content
            # Content format: "Found {title}, {price}, {location} - listing ID {id}"
            stored_record = results[0]
            content = stored_record.get('content', '')
            
            # Parse price from content more carefully
            # Content format: "Found {title}, {price}, {location} - listing ID {id}"
            # Extract price using regex to handle commas in prices
            import re
            
            # Match currency symbol followed by digits and optional commas
            # Stop at comma followed by space (which separates price from location)
            price_pattern = r'[\$€£][\d,]+(?=\s*,\s|$)'
            prices_in_content = re.findall(price_pattern, content)
            
            if prices_in_content:
                stored_price = prices_in_content[0]
                
                # Compare prices
                if stored_price != current_price:
                    return (stored_price, current_price)
            
            return None
        except Exception:
            return None
