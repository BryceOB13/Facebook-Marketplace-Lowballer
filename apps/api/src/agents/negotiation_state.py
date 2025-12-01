"""
Negotiation State Machine

Tracks conversation state WITHOUT generating messages.
Claude 3 Haiku generates all messages intelligently.
This just tracks where we are in the negotiation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class NegotiationStatus(str, Enum):
    """Current state of the negotiation."""
    IDLE = "idle"
    INITIAL_CONTACT = "initial_contact"
    NEGOTIATING = "negotiating"
    AWAITING_RESPONSE = "awaiting_response"
    COUNTER_RECEIVED = "counter_received"
    DEAL_ACCEPTED = "deal_accepted"
    SCHEDULING_MEETUP = "scheduling_meetup"
    WALKED_AWAY = "walked_away"
    DECLINED = "declined"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user" (us) or "seller"
    content: str
    timestamp: datetime
    offer_amount: Optional[float] = None


@dataclass
class NegotiationState:
    """Tracks the full state of a negotiation."""
    listing_id: str
    status: NegotiationStatus = NegotiationStatus.IDLE
    
    # Offer tracking
    our_initial_offer: Optional[float] = None
    our_last_offer: Optional[float] = None
    seller_last_offer: Optional[float] = None
    agreed_price: Optional[float] = None
    
    # Conversation history
    message_history: List[Message] = field(default_factory=list)
    messages_sent: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    # Walk-away tracking
    walk_away_price: Optional[float] = None
    walk_away_reason: Optional[str] = None
    
    # Meetup details
    meetup_location: Optional[str] = None
    meetup_time: Optional[str] = None
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update state from parsed agent output."""
        for key, value in updates.items():
            if hasattr(self, key):
                if key == "status" and isinstance(value, str):
                    value = NegotiationStatus(value)
                setattr(self, key, value)
        self.last_message_at = datetime.now()
    
    def record_our_message(self, content: str, offer: Optional[float] = None) -> None:
        """Record a message we sent."""
        self.message_history.append(Message(
            role="user",
            content=content,
            timestamp=datetime.now(),
            offer_amount=offer
        ))
        self.messages_sent += 1
        self.last_message_at = datetime.now()
        
        if offer:
            if self.our_initial_offer is None:
                self.our_initial_offer = offer
            self.our_last_offer = offer
    
    def record_seller_message(self, content: str, offer: Optional[float] = None) -> None:
        """Record a message from the seller."""
        self.message_history.append(Message(
            role="seller",
            content=content,
            timestamp=datetime.now(),
            offer_amount=offer
        ))
        self.last_message_at = datetime.now()
        if offer:
            self.seller_last_offer = offer
    
    def should_walk_away(self, proposed_price: float) -> bool:
        """Check if we should walk away from this price."""
        if self.walk_away_price is None:
            return False
        return proposed_price > self.walk_away_price
    
    def can_counter(self, max_counters: int = 3) -> bool:
        """Check if we can make another counter-offer."""
        our_offers = [m for m in self.message_history if m.role == "user" and m.offer_amount]
        return len(our_offers) < max_counters
    
    def get_negotiation_progress(self) -> Dict:
        """Get summary of negotiation progress."""
        return {
            "status": self.status.value,
            "our_offers": [m.offer_amount for m in self.message_history if m.role == "user" and m.offer_amount],
            "seller_offers": [m.offer_amount for m in self.message_history if m.role == "seller" and m.offer_amount],
            "messages_exchanged": len(self.message_history),
            "can_counter": self.can_counter(),
            "time_elapsed_minutes": self._time_elapsed_minutes()
        }
    
    def _time_elapsed_minutes(self) -> Optional[float]:
        if self.started_at:
            delta = datetime.now() - self.started_at
            return delta.total_seconds() / 60
        return None
    
    def to_dict(self) -> Dict:
        """Serialize state for storage/transmission."""
        return {
            "listing_id": self.listing_id,
            "status": self.status.value,
            "our_initial_offer": self.our_initial_offer,
            "our_last_offer": self.our_last_offer,
            "seller_last_offer": self.seller_last_offer,
            "agreed_price": self.agreed_price,
            "messages_sent": self.messages_sent,
            "message_count": len(self.message_history),
            "walk_away_price": self.walk_away_price,
            "walk_away_reason": self.walk_away_reason,
            "meetup_location": self.meetup_location,
            "meetup_time": self.meetup_time
        }
