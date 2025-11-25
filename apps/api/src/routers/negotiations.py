"""
Negotiation routes for lowball mode.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from src.models import Negotiation, NegotiationCreate, Listing
from src.services.negotiation import NegotiationManager
from src.db import get_pg_pool

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/negotiations", response_model=Negotiation)
async def start_negotiation(
    listing_id: str,
    max_budget: int
):
    """
    Start a new negotiation for a listing.
    
    Args:
        listing_id: Listing ID to negotiate for
        max_budget: Maximum budget for this negotiation
        
    Returns:
        Created Negotiation with initial offer suggestion
    """
    try:
        # Fetch listing
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM listings WHERE id = $1
            """, listing_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Convert to Listing
        listing = Listing(
            id=row['id'],
            title=row['title'],
            price=row['price'],
            price_value=row['price_value'],
            location=row['location'],
            image_url=row['image_url'],
            url=row['url'],
            seller_name=row['seller_name'],
            scraped_at=row['scraped_at'],
            created_at=row['created_at']
        )
        
        # Create negotiation
        manager = NegotiationManager()
        negotiation = await manager.create_negotiation(listing, max_budget)
        
        return negotiation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/negotiations", response_model=List[Negotiation])
async def list_negotiations(
    state: Optional[str] = Query(None, description="Filter by state")
):
    """
    List all negotiations, optionally filtered by state.
    """
    try:
        manager = NegotiationManager()
        negotiations = await manager.list_negotiations(state)
        return negotiations
    except Exception as e:
        logger.error(f"Failed to list negotiations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/negotiations/{negotiation_id}", response_model=Negotiation)
async def get_negotiation(negotiation_id: int):
    """
    Get a single negotiation by ID.
    """
    try:
        manager = NegotiationManager()
        negotiation = await manager.get_negotiation(negotiation_id)
        
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")
        
        return negotiation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/negotiations/{negotiation_id}/send", response_model=Negotiation)
async def send_offer(
    negotiation_id: int,
    offer: int,
    message: str
):
    """
    Send an offer in a negotiation.
    
    Args:
        negotiation_id: Negotiation ID
        offer: Offer amount
        message: Message to send to seller
        
    Returns:
        Updated negotiation
    """
    try:
        manager = NegotiationManager()
        negotiation = await manager.update_negotiation(
            negotiation_id,
            "send_offer",
            {"offer": offer, "message": message}
        )
        return negotiation
    except Exception as e:
        logger.error(f"Failed to send offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/negotiations/{negotiation_id}/response", response_model=Negotiation)
async def record_response(
    negotiation_id: int,
    seller_message: str,
    seller_counter: Optional[int] = None
):
    """
    Record seller's response to an offer.
    
    Args:
        negotiation_id: Negotiation ID
        seller_message: Seller's message
        seller_counter: Seller's counter offer (optional)
        
    Returns:
        Updated negotiation with recommended action
    """
    try:
        manager = NegotiationManager()
        negotiation = await manager.update_negotiation(
            negotiation_id,
            "receive_response",
            {
                "seller_message": seller_message,
                "seller_counter": seller_counter
            }
        )
        return negotiation
    except Exception as e:
        logger.error(f"Failed to record response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
