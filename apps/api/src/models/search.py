"""Search data models"""

from pydantic import BaseModel
from typing import Optional, List, Union
from .listing import Listing
from .deal import Deal


class SearchQuery(BaseModel):
    """Search query parameters"""
    query: str
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    location: Optional[str] = None
    category: Optional[str] = None


class SearchResult(BaseModel):
    """Search results with metadata"""
    listings: List[Union[Listing, Deal]]  # Can return either listings or scored deals
    total_count: int
    query_variations: List[str] = []
    cached: bool = False
    search_time_ms: Optional[float] = None
