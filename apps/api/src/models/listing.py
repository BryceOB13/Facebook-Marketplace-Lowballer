"""Listing data models"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ListingBase(BaseModel):
    """Base listing fields"""
    title: str
    price: str
    price_value: Optional[int] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    url: str
    seller_name: Optional[str] = None


class ListingCreate(ListingBase):
    """Model for creating a new listing"""
    id: str
    scraped_at: datetime = Field(default_factory=datetime.now)
    match_score: Optional[float] = None
    match_reason: Optional[str] = None


class Listing(ListingBase):
    """Complete listing model"""
    id: str
    scraped_at: datetime
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ListingResponse(Listing):
    """API response model for listings"""
    pass
