"""Search data models"""

from pydantic import BaseModel
from typing import Optional, List
from .listing import Listing


class SearchQuery(BaseModel):
    """Search query parameters"""
    query: str
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    location: Optional[str] = None
    category: Optional[str] = None


class SearchResult(BaseModel):
    """Search results with metadata"""
    listings: List[Listing]
    total_count: int
    query_variations: List[str] = []
    cached: bool = False
    search_time_ms: Optional[float] = None
