"""
Negotiation Agent API Endpoints

Handles "Negotiate" button clicks from Deal Scout UI.
Provides SSE streaming for real-time updates.
"""

import asyncio
import json
import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents import (
    start_negotiation,
    ListingContext,
    NegotiationMode,
    StrategySelector,
    STRATEGIES
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/negotiate", tags=["negotiate"])

# In-memory storage for demo (replace with Redis in production)
negotiation_streams: dict = {}
negotiation_data: dict = {}


class NegotiateRequest(BaseModel):
    """Request body when Negotiate button is clicked."""
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
    mode: str = "review"


class NegotiationBoundsRequest(BaseModel):
    """Request to calculate negotiation bounds."""
    asking_price: float
    market_avg: float
    deal_rating: str
    listing_age_days: Optional[int] = None
    user_strategy: Optional[str] = None  # Override: shrewd, moderate, lenient, accept


class NegotiationBoundsResponse(BaseModel):
    """Negotiation bounds and strategy info."""
    strategy_name: str
    strategy_tier: str
    initial_offer: float
    target_price: float
    walk_away_price: float
    max_increase_per_round_pct: float
    tone_guidance: str
    opening_approach: str


class NegotiationStatusResponse(BaseModel):
    """Response with negotiation status."""
    negotiation_id: str
    status: str
    listing_id: str


@router.post("/bounds", response_model=NegotiationBoundsResponse)
async def get_negotiation_bounds(request: NegotiationBoundsRequest):
    """
    Calculate negotiation bounds for a listing.
    Called when deal modal opens to show strategy info.
    """
    selector = StrategySelector()
    strategy = selector.select_strategy(
        asking_price=request.asking_price,
        market_avg=request.market_avg,
        deal_rating=request.deal_rating,
        listing_age_days=request.listing_age_days,
        user_override=request.user_strategy
    )
    
    initial_offer = strategy.calculate_initial_offer(request.asking_price)
    
    # Use market_avg if provided, otherwise estimate from asking price
    market_avg = request.market_avg if request.market_avg > 0 else request.asking_price * 1.5
    
    # Calculate walk-away price based on strategy tier
    # Walk-away should give room to negotiate between initial and walk-away
    if strategy.tier.value == "accept":
        # Accept strategy: buy at listed price
        walk_away = request.asking_price
        initial_offer = request.asking_price
        target_price = request.asking_price
    elif strategy.tier.value == "shrewd":
        # Shrewd: initial at 50%, walk-away at 75% of asking
        walk_away = request.asking_price * 0.75
        target_price = request.asking_price * 0.60
    elif strategy.tier.value == "moderate":
        # Moderate: initial at 70%, walk-away at 90% of asking
        walk_away = request.asking_price * 0.90
        target_price = request.asking_price * 0.80
    else:
        # Lenient: initial at 85%, walk-away at 95% of asking
        walk_away = request.asking_price * 0.95
        target_price = request.asking_price * 0.90
    
    # Ensure walk_away > initial_offer for negotiation room
    if walk_away <= initial_offer:
        walk_away = initial_offer * 1.2
    
    # Cap walk_away at asking price
    walk_away = min(walk_away, request.asking_price)
    
    return NegotiationBoundsResponse(
        strategy_name=strategy.name,
        strategy_tier=strategy.tier.value,
        initial_offer=initial_offer,
        target_price=target_price,
        walk_away_price=walk_away,
        max_increase_per_round_pct=strategy.max_increase_per_round * 100,
        tone_guidance=strategy.tone_guidance,
        opening_approach=strategy.opening_approach
    )


@router.post("/start", response_model=NegotiationStatusResponse)
async def start_negotiation_endpoint(
    request: NegotiateRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new negotiation.
    Returns immediately with negotiation ID.
    Client should connect to SSE endpoint for updates.
    """
    negotiation_id = f"neg_{request.listing_id}_{int(time.time())}"
    
    negotiation_data[negotiation_id] = {
        "_id": negotiation_id,
        "listing_id": request.listing_id,
        "status": "starting",
        "request": request.dict(),
        "created_at": time.time()
    }
    
    negotiation_streams[negotiation_id] = asyncio.Queue()
    
    background_tasks.add_task(
        run_negotiation_task,
        negotiation_id,
        request
    )
    
    return NegotiationStatusResponse(
        negotiation_id=negotiation_id,
        status="starting",
        listing_id=request.listing_id
    )


@router.get("/stream/{negotiation_id}")
async def stream_negotiation(negotiation_id: str):
    """SSE endpoint for real-time negotiation updates."""
    
    async def event_generator():
        if negotiation_id not in negotiation_streams:
            yield f"event: error\n"
            yield f'data: {{"message": "Negotiation not found"}}\n\n'
            return
        
        queue = negotiation_streams[negotiation_id]
        
        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    yield f"event: {event_data['type']}\n"
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                    if event_data['type'] in ['negotiation_complete', 'error']:
                        break
                        
                except asyncio.TimeoutError:
                    yield f"event: keepalive\n"
                    yield f'data: {{"timestamp": {time.time()}}}\n\n'
                    
        except Exception as e:
            logger.error(f"Stream error for {negotiation_id}: {e}")
            yield f"event: error\n"
            yield f'data: {{"message": "{str(e)}"}}\n\n'
        finally:
            if negotiation_id in negotiation_streams:
                del negotiation_streams[negotiation_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/approve/{negotiation_id}")
async def approve_message(negotiation_id: str):
    """Approve pending message in review mode."""
    if negotiation_id in negotiation_streams:
        await negotiation_streams[negotiation_id].put({
            "type": "user_approval",
            "approved": True
        })
    return {"status": "approved"}


@router.post("/reject/{negotiation_id}")
async def reject_message(negotiation_id: str, feedback: Optional[str] = None):
    """Reject pending message in review mode."""
    if negotiation_id in negotiation_streams:
        await negotiation_streams[negotiation_id].put({
            "type": "user_approval",
            "approved": False,
            "feedback": feedback
        })
    return {"status": "rejected"}


@router.post("/abort/{negotiation_id}")
async def abort_negotiation(negotiation_id: str):
    """Abort an ongoing negotiation."""
    if negotiation_id in negotiation_streams:
        await negotiation_streams[negotiation_id].put({
            "type": "abort",
            "reason": "user_requested"
        })
    
    if negotiation_id in negotiation_data:
        negotiation_data[negotiation_id]["status"] = "aborted"
    
    return {"status": "aborted"}


@router.get("/status/{negotiation_id}")
async def get_negotiation_status(negotiation_id: str):
    """Get current negotiation status."""
    if negotiation_id not in negotiation_data:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation_data[negotiation_id]


class SendMessageRequest(BaseModel):
    """Request to type a message into Facebook Messenger."""
    listing_url: str
    message: str
    offer_amount: Optional[float] = None


@router.post("/send-message")
async def send_message_to_facebook(request: SendMessageRequest):
    """
    Type a message into the Facebook Messenger input box.
    Does NOT click send - user controls that.
    """
    from src.services.browser.mcp_client import BrowserMCPClient
    
    try:
        async with BrowserMCPClient() as browser:
            # Navigate to listing if not already there
            current_url = await browser.evaluate_script("window.location.href")
            
            if request.listing_url not in current_url:
                await browser.navigate(request.listing_url)
                await browser.wait_for_selector('[aria-label="Message seller"]', timeout=5000)
            
            # Try to find and click "Message Seller" button if visible
            try:
                await browser.click('[aria-label="Message seller"]')
                await asyncio.sleep(1)
            except Exception:
                pass  # May already be in message view
            
            # Find the message input - try multiple selectors
            input_selectors = [
                'div[aria-label="Message"]',
                'textarea[placeholder*="message"]',
                'div[contenteditable="true"]',
                'input[placeholder*="Message"]'
            ]
            
            input_found = False
            for selector in input_selectors:
                try:
                    # Clear existing text and type new message
                    await browser.evaluate_script(f'''
                        const input = document.querySelector('{selector}');
                        if (input) {{
                            input.focus();
                            if (input.tagName === 'DIV') {{
                                input.textContent = '';
                            }} else {{
                                input.value = '';
                            }}
                        }}
                    ''')
                    await browser.fill(selector, request.message)
                    input_found = True
                    break
                except Exception:
                    continue
            
            if not input_found:
                return {
                    "status": "error",
                    "message": "Could not find message input. Make sure you're on the listing page."
                }
            
            return {
                "status": "typed",
                "message": "Message typed into Facebook. Click Send when ready.",
                "offer_amount": request.offer_amount
            }
            
    except Exception as e:
        logger.error(f"Failed to type message: {e}")
        return {
            "status": "error", 
            "message": f"Failed to type message: {str(e)}"
        }


async def run_negotiation_task(
    negotiation_id: str,
    request: NegotiateRequest
):
    """Background task that runs the negotiation agent."""
    
    listing = ListingContext(
        listing_id=request.listing_id,
        listing_url=request.listing_url,
        item_title=request.item_title,
        asking_price=request.asking_price,
        market_avg=request.market_avg,
        deal_rating=request.deal_rating,
        profit_estimate=request.profit_estimate,
        roi_percent=request.roi_percent,
        seller_name=request.seller_name,
        listing_age_days=request.listing_age_days,
        description=request.description,
        condition=request.condition,
        user_max_price=request.user_max_price,
        user_strategy=request.user_strategy,
        user_meeting_preference=request.user_meeting_preference
    )
    
    mode = NegotiationMode(request.mode)
    
    async def status_callback(update: dict):
        update["negotiation_id"] = negotiation_id
        
        if negotiation_id in negotiation_streams:
            await negotiation_streams[negotiation_id].put(update)
        
        if update.get("type") == "state_update":
            if negotiation_id in negotiation_data:
                negotiation_data[negotiation_id]["state"] = update.get("state")
    
    try:
        result = await start_negotiation(
            listing=listing,
            mode=mode,
            status_callback=status_callback
        )
        
        if negotiation_id in negotiation_data:
            negotiation_data[negotiation_id].update({
                "status": result.status,
                "result": {
                    "final_price": result.final_price,
                    "messages_sent": result.messages_sent,
                    "walk_away_reason": result.walk_away_reason
                }
            })
        
        if negotiation_id in negotiation_streams:
            await negotiation_streams[negotiation_id].put({
                "type": "negotiation_complete",
                "result": {
                    "status": result.status,
                    "final_price": result.final_price,
                    "messages_sent": result.messages_sent
                }
            })
        
    except Exception as e:
        logger.error(f"Negotiation task failed: {e}")
        
        if negotiation_id in negotiation_data:
            negotiation_data[negotiation_id].update({
                "status": "error", 
                "error": str(e)
            })
        
        if negotiation_id in negotiation_streams:
            await negotiation_streams[negotiation_id].put({
                "type": "error",
                "message": str(e)
            })
