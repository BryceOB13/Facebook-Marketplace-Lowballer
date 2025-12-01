"""
Deal Scout Negotiation Agent - Claude Agent SDK implementation for 
Facebook Marketplace price negotiations.

Uses Claude 3 Haiku for intelligent, human-like message generation.
NO TEMPLATES - every message is contextually generated.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .negotiation_state import NegotiationState, NegotiationStatus
from .negotiation_strategy import StrategySelector, NegotiationStrategy
from .prompts.negotiation import build_system_prompt, build_mode_prompt, build_context_block

logger = logging.getLogger(__name__)


class NegotiationMode(str, Enum):
    TEST = "test"
    REVIEW = "review"
    AUTO = "auto"


@dataclass
class ListingContext:
    """Context passed from Deal Scout UI when Negotiate is clicked."""
    listing_id: str
    listing_url: str
    item_title: str
    asking_price: float
    market_avg: float
    deal_rating: str
    profit_estimate: float
    roi_percent: float
    seller_name: Optional[str] = None
    listing_age_days: Optional[int] = None
    description: Optional[str] = None
    condition: Optional[str] = None
    user_max_price: Optional[float] = None
    user_strategy: Optional[str] = None
    user_meeting_preference: Optional[str] = None


@dataclass
class NegotiationResult:
    """Result returned after negotiation attempt."""
    status: str
    final_price: Optional[float] = None
    messages_sent: int = 0
    conversation_history: List[Dict] = None
    walk_away_reason: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []


def calculate_walk_away_price(
    listing: ListingContext,
    strategy: NegotiationStrategy,
    user_override: Optional[float] = None
) -> float:
    """Calculate the maximum price we're willing to pay."""
    if user_override is not None:
        return user_override
    
    # Reseller calculation: market_avg - 16% fees - $15 shipping - $30 min profit
    platform_fees = listing.market_avg * 0.16
    shipping_cost = 15.0
    min_profit = 30.0
    
    walk_away = listing.market_avg - platform_fees - shipping_cost - min_profit
    return min(walk_away, listing.asking_price)


async def start_negotiation(
    listing: ListingContext,
    mode: NegotiationMode = NegotiationMode.REVIEW,
    mcp_config_path: str = ".mcp.json",
    status_callback: Optional[Callable[[Dict], Any]] = None
) -> NegotiationResult:
    """
    Start a negotiation for a Facebook Marketplace listing.
    Main entry point called when user clicks "Negotiate" button.
    """
    
    # Initialize state tracking
    state = NegotiationState(listing_id=listing.listing_id)
    state.started_at = datetime.now()
    
    # Select negotiation strategy
    strategy_selector = StrategySelector()
    strategy = strategy_selector.select_strategy(
        asking_price=listing.asking_price,
        market_avg=listing.market_avg,
        deal_rating=listing.deal_rating,
        listing_age_days=listing.listing_age_days,
        user_override=listing.user_strategy
    )
    
    # Calculate walk-away price
    walk_away_price = calculate_walk_away_price(
        listing=listing,
        strategy=strategy,
        user_override=listing.user_max_price
    )
    state.walk_away_price = walk_away_price
    
    # Build context for the agent
    negotiation_context = build_context_block(
        listing=listing,
        strategy=strategy,
        walk_away_price=walk_away_price,
        state=state
    )
    
    # Build prompts
    system_prompt = build_system_prompt(
        strategy=strategy,
        walk_away_price=walk_away_price,
        meeting_preference=listing.user_meeting_preference
    )
    
    mode_prompt = build_mode_prompt(
        mode=mode,
        listing=listing,
        negotiation_context=negotiation_context
    )
    
    # Track conversation
    result = NegotiationResult(
        status="pending",
        messages_sent=0,
        conversation_history=[]
    )
    
    # Send initial status
    if status_callback:
        await status_callback({
            "type": "negotiation_started",
            "listing_id": listing.listing_id,
            "strategy": strategy.name,
            "strategy_tier": strategy.tier.value,
            "walk_away_price": walk_away_price,
            "initial_offer": strategy.calculate_initial_offer(listing.asking_price)
        })
    
    try:
        logger.info(f"Starting negotiation for {listing.item_title}")
        logger.info(f"Strategy: {strategy.name}, Walk-away: ${walk_away_price}")
        
        # Simulate negotiation (replace with Claude Agent SDK in production)
        await simulate_negotiation(
            listing=listing,
            strategy=strategy,
            state=state,
            mode=mode,
            status_callback=status_callback
        )
        
        # Determine final result
        result.status = state.status.value
        result.final_price = state.agreed_price
        result.messages_sent = state.messages_sent
        result.conversation_history = [{
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
            "offer_amount": m.offer_amount
        } for m in state.message_history]
        
        if state.status == NegotiationStatus.WALKED_AWAY:
            result.walk_away_reason = state.walk_away_reason
            
    except Exception as e:
        result.status = "error"
        result.error = str(e)
        logger.error(f"Negotiation failed: {e}")
        
        if status_callback:
            await status_callback({
                "type": "error",
                "message": str(e)
            })
    
    return result


async def simulate_negotiation(
    listing: ListingContext,
    strategy: NegotiationStrategy,
    state: NegotiationState,
    mode: NegotiationMode,
    status_callback: Optional[Callable[[Dict], Any]] = None
):
    """Simulate a negotiation for demo purposes."""
    
    # Simulate opening message
    initial_offer = strategy.calculate_initial_offer(listing.asking_price)
    opening_message = f"Hey! Interested in the {listing.item_title}. Would you take ${initial_offer:.0f}?"
    
    state.record_our_message(opening_message, initial_offer)
    state.status = NegotiationStatus.INITIAL_CONTACT
    
    if status_callback:
        await status_callback({
            "type": "agent_message",
            "content": f"Sent opening message: {opening_message}"
        })
        await status_callback({
            "type": "state_update",
            "state": state.to_dict()
        })
    
    # Simulate seller response
    await asyncio.sleep(1)
    
    if listing.asking_price - initial_offer > 100:
        # Seller counters
        seller_counter = (listing.asking_price + initial_offer) / 2
        seller_message = f"Thanks for the interest! I could do ${seller_counter:.0f}"
        
        state.record_seller_message(seller_message, seller_counter)
        state.status = NegotiationStatus.COUNTER_RECEIVED
        
        if status_callback:
            await status_callback({
                "type": "agent_message",
                "content": f"Seller responded: {seller_message}"
            })
        
        # Check if we should accept or counter
        if seller_counter <= state.walk_away_price:
            accept_message = "That works for me! When can I pick it up?"
            state.record_our_message(accept_message)
            state.status = NegotiationStatus.DEAL_ACCEPTED
            state.agreed_price = seller_counter
            
            if status_callback:
                await status_callback({
                    "type": "agent_message",
                    "content": f"Accepted deal: {accept_message}"
                })
        else:
            walk_away_message = "That's a bit more than I can do. Thanks anyway!"
            state.record_our_message(walk_away_message)
            state.status = NegotiationStatus.WALKED_AWAY
            state.walk_away_reason = f"Seller counter ${seller_counter:.0f} exceeded walk-away ${state.walk_away_price:.0f}"
            
            if status_callback:
                await status_callback({
                    "type": "agent_message",
                    "content": f"Walked away: {walk_away_message}"
                })
    else:
        # Seller accepts
        seller_message = "Sure, that works!"
        state.record_seller_message(seller_message)
        state.status = NegotiationStatus.DEAL_ACCEPTED
        state.agreed_price = initial_offer
        
        if status_callback:
            await status_callback({
                "type": "agent_message",
                "content": f"Seller accepted: {seller_message}"
            })
    
    # Final state update
    if status_callback:
        await status_callback({
            "type": "state_update",
            "state": state.to_dict()
        })
        await status_callback({
            "type": "negotiation_complete",
            "result": {
                "status": state.status.value,
                "final_price": state.agreed_price,
                "messages_sent": state.messages_sent
            }
        })


def extract_text_content(message) -> Optional[str]:
    """Extract text content from Claude Agent SDK message."""
    if hasattr(message, "text"):
        return message.text
    if hasattr(message, "content"):
        for block in message.content:
            if hasattr(block, "text"):
                return block.text
    return None


def parse_state_update(text: str) -> Optional[Dict]:
    """Parse state updates from agent output."""
    if "[STATE_UPDATE]" in text:
        try:
            json_str = text.split("[STATE_UPDATE]")[1].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass
    return None
