"""Deal data models"""

from pydantic import BaseModel
from enum import Enum
from typing import Optional
from .listing import Listing


class DealRating(str, Enum):
    """Deal quality rating"""
    HOT = "HOT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    PASS = "PASS"


class Deal(Listing):
    """Deal model extending Listing with scoring data"""
    ebay_avg_price: Optional[float] = None
    profit_estimate: Optional[float] = None
    roi_percent: Optional[float] = None
    deal_rating: DealRating
    is_new: bool = True
    price_changed: bool = False
    old_price: Optional[str] = None
    
    # Additional deal-specific fields
    why_standout: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True
