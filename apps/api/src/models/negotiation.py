"""Negotiation data models"""

from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional


class NegotiationState(str, Enum):
    """Negotiation state machine states"""
    IDLE = "idle"
    COMPOSING = "composing"
    SENT = "sent"
    AWAITING = "awaiting"
    COUNTERING = "countering"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class NegotiationMessage(BaseModel):
    """Single message in negotiation"""
    role: str  # "user" or "seller"
    content: str
    amount: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class NegotiationCreate(BaseModel):
    """Model for creating a new negotiation"""
    listing_id: str
    max_budget: int


class Negotiation(BaseModel):
    """Complete negotiation model"""
    id: int
    listing_id: str
    state: NegotiationState
    asking_price: int
    current_offer: int
    max_budget: int
    round_number: int = 0
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    suggested_offer: Optional[int] = None
    suggested_message: Optional[str] = None
    recommended_action: Optional[str] = None
    
    class Config:
        from_attributes = True


class NegotiationResponse(Negotiation):
    """API response model for negotiations"""
    pass
