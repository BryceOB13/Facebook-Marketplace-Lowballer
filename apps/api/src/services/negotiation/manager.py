"""
Negotiation manager - Handles persistence and retrieval of negotiations.
"""

import logging
from typing import List, Optional
from datetime import datetime

from src.models import Negotiation, NegotiationCreate, Listing
from src.db import get_pg_pool
from .state_machine import NegotiationStateMachine

logger = logging.getLogger(__name__)


class NegotiationManager:
    """Manage negotiation persistence and lifecycle"""
    
    async def create_negotiation(
        self, 
        listing: Listing, 
        max_budget: int
    ) -> Negotiation:
        """
        Create a new negotiation.
        
        Args:
            listing: Listing to negotiate for
            max_budget: Maximum budget for this negotiation
            
        Returns:
            Created Negotiation object
        """
        # Create state machine
        machine = NegotiationStateMachine(listing, max_budget)
        initial_state = machine.start()
        
        # Save to database
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO negotiations (
                    listing_id, state, asking_price, current_offer,
                    max_budget, round_number, messages
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, created_at, updated_at
            """, 
                listing.id,
                initial_state['state'],
                machine.asking_price,
                initial_state['suggested_offer'],
                max_budget,
                initial_state['round'],
                []
            )
            
            return Negotiation(
                id=row['id'],
                listing_id=listing.id,
                state=initial_state['state'],
                asking_price=machine.asking_price,
                current_offer=initial_state['suggested_offer'],
                max_budget=max_budget,
                round_number=initial_state['round'],
                messages=[],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                suggested_offer=initial_state['suggested_offer'],
                suggested_message=initial_state['suggested_message']
            )
    
    async def get_negotiation(self, negotiation_id: int) -> Optional[Negotiation]:
        """
        Get negotiation by ID.
        
        Args:
            negotiation_id: Negotiation ID
            
        Returns:
            Negotiation object or None
        """
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM negotiations WHERE id = $1
            """, negotiation_id)
            
            if not row:
                return None
            
            return Negotiation(
                id=row['id'],
                listing_id=row['listing_id'],
                state=row['state'],
                asking_price=row['asking_price'],
                current_offer=row['current_offer'],
                max_budget=row['max_budget'],
                round_number=row['round_number'],
                messages=row['messages'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def list_negotiations(
        self, 
        state: Optional[str] = None
    ) -> List[Negotiation]:
        """
        List all negotiations, optionally filtered by state.
        
        Args:
            state: Filter by state (optional)
            
        Returns:
            List of Negotiation objects
        """
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            if state:
                rows = await conn.fetch("""
                    SELECT * FROM negotiations 
                    WHERE state = $1
                    ORDER BY updated_at DESC
                """, state)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM negotiations 
                    ORDER BY updated_at DESC
                """)
            
            return [
                Negotiation(
                    id=row['id'],
                    listing_id=row['listing_id'],
                    state=row['state'],
                    asking_price=row['asking_price'],
                    current_offer=row['current_offer'],
                    max_budget=row['max_budget'],
                    round_number=row['round_number'],
                    messages=row['messages'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in rows
            ]
    
    async def update_negotiation(
        self,
        negotiation_id: int,
        action: str,
        data: dict
    ) -> Negotiation:
        """
        Update negotiation state based on action.
        
        Args:
            negotiation_id: Negotiation ID
            action: Action to perform (send_offer, receive_response)
            data: Action data
            
        Returns:
            Updated Negotiation object
        """
        # Get current negotiation
        negotiation = await self.get_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found")
        
        # Reconstruct state machine
        # Note: In production, you'd fetch the listing from DB
        from src.models import Listing
        listing = Listing(
            id=negotiation.listing_id,
            title="",  # Would fetch from DB
            price="",
            url="",
            scraped_at=datetime.now(),
            created_at=datetime.now(),
            price_value=negotiation.asking_price
        )
        
        machine = NegotiationStateMachine(listing, negotiation.max_budget)
        machine.state = negotiation.state
        machine.current_offer = negotiation.current_offer
        machine.round = negotiation.round_number
        machine.messages = negotiation.messages
        
        # Perform action
        if action == "send_offer":
            result = machine.send_offer(
                data.get('offer'),
                data.get('message')
            )
        elif action == "receive_response":
            result = machine.receive_response(
                data.get('seller_message'),
                data.get('seller_counter')
            )
        else:
            raise ValueError(f"Unknown action: {action}")
        
        # Update database
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE negotiations
                SET state = $1, current_offer = $2, round_number = $3,
                    messages = $4, updated_at = NOW()
                WHERE id = $5
            """,
                machine.state,
                machine.current_offer,
                machine.round,
                machine.messages,
                negotiation_id
            )
        
        # Return updated negotiation
        updated = await self.get_negotiation(negotiation_id)
        
        # Add suggested actions from result
        if 'suggested_offer' in result:
            updated.suggested_offer = result['suggested_offer']
        if 'suggested_message' in result:
            updated.suggested_message = result['suggested_message']
        if 'recommended_action' in result:
            updated.recommended_action = result['recommended_action']
        
        return updated
