"""Data models for Deal Scout API"""

from .listing import Listing, ListingCreate, ListingResponse
from .deal import Deal, DealRating
from .negotiation import Negotiation, NegotiationState, NegotiationCreate
from .search import SearchQuery, SearchResult

__all__ = [
    "Listing",
    "ListingCreate",
    "ListingResponse",
    "Deal",
    "DealRating",
    "Negotiation",
    "NegotiationState",
    "NegotiationCreate",
    "SearchQuery",
    "SearchResult",
]
