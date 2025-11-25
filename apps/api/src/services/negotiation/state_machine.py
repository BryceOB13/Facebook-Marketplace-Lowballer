"""
Negotiation state machine - Pure Python implementation.
Uses LLM for message generation and response analysis.
"""

import logging
import os
from typing import Dict, Optional, List
from datetime import datetime
import anthropic

from src.models import Listing, NegotiationState

logger = logging.getLogger(__name__)


class NegotiationStateMachine:
    """
    State machine for managing lowball negotiations.
    Uses Claude Haiku for intelligent message generation and response analysis.
    """
    
    STATES = [
        "idle", "composing", "sent", "awaiting", 
        "countering", "accepted", "rejected", "abandoned"
    ]
    
    def __init__(self, listing: Listing, max_budget: int):
        self.listing = listing
        self.asking_price = listing.price_value or 0
        self.max_budget = max_budget
        self.current_offer = 0
        self.state = "idle"
        self.round = 0
        self.messages: List[Dict] = []
        
        # Initialize LLM client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.use_llm = self.client is not None
    
    def start(self) -> Dict:
        """
        Start negotiation by calculating initial offer.
        
        Returns:
            Dict with state, suggested_offer, suggested_message
        """
        if self.state != "idle":
            raise ValueError(f"Cannot start from state: {self.state}")
        
        # Calculate initial offer at 65% of asking price
        self.current_offer = int(self.asking_price * 0.65)
        self.state = "composing"
        self.round = 1
        
        # Generate message using LLM
        message = self._generate_message("initial_offer")
        
        return {
            "state": self.state,
            "suggested_offer": self.current_offer,
            "suggested_message": message,
            "round": self.round
        }
    
    def send_offer(self, offer: int, message: str) -> Dict:
        """
        Record that an offer was sent.
        
        Args:
            offer: Offer amount
            message: Message sent to seller
            
        Returns:
            Updated state dict
        """
        if self.state != "composing":
            raise ValueError(f"Cannot send offer from state: {self.state}")
        
        self.current_offer = offer
        self.messages.append({
            "role": "user",
            "content": message,
            "amount": offer,
            "timestamp": datetime.now().isoformat()
        })
        
        self.state = "awaiting"
        
        return self.get_state()
    
    def receive_response(
        self, 
        seller_message: str, 
        seller_counter: Optional[int] = None
    ) -> Dict:
        """
        Process seller's response and determine next action.
        
        Args:
            seller_message: Seller's message
            seller_counter: Seller's counter offer (if any)
            
        Returns:
            Dict with state, recommended_action, suggested_counter
        """
        if self.state != "awaiting":
            raise ValueError(f"Cannot receive response from state: {self.state}")
        
        # Record seller message
        self.messages.append({
            "role": "seller",
            "content": seller_message,
            "amount": seller_counter,
            "timestamp": datetime.now().isoformat()
        })
        
        # Analyze response using LLM
        analysis = self._analyze_response(seller_message, seller_counter)
        
        intent = analysis.get("intent", "counter")
        
        if intent == "acceptance":
            self.state = "accepted"
            return {
                "state": self.state,
                "recommended_action": "accept",
                "message": "Deal accepted! Arrange pickup."
            }
        
        elif intent == "rejection":
            self.state = "rejected"
            return {
                "state": self.state,
                "recommended_action": "walk_away",
                "message": "Seller rejected. Move on to next deal."
            }
        
        elif intent == "counter" and seller_counter:
            self.state = "countering"
            self.round += 1
            
            # Calculate new offer using decreasing concession
            new_offer = self._calculate_counter_offer(seller_counter)
            
            if new_offer > self.max_budget:
                # Check if seller is close to budget
                if seller_counter <= self.max_budget * 1.05:
                    # Final offer at budget
                    message = self._generate_message("final_offer", {
                        "final_offer": self.max_budget,
                        "seller_counter": seller_counter
                    })
                    return {
                        "state": self.state,
                        "recommended_action": "final_offer",
                        "suggested_offer": self.max_budget,
                        "suggested_message": message,
                        "round": self.round
                    }
                else:
                    # Walk away
                    self.state = "abandoned"
                    message = self._generate_message("walk_away")
                    return {
                        "state": self.state,
                        "recommended_action": "walk_away",
                        "suggested_message": message
                    }
            
            # Generate counter offer message
            message = self._generate_message("counter_offer", {
                "new_offer": new_offer,
                "seller_counter": seller_counter,
                "gap": seller_counter - new_offer
            })
            
            return {
                "state": self.state,
                "recommended_action": "counter",
                "suggested_offer": new_offer,
                "suggested_message": message,
                "round": self.round
            }
        
        else:
            # Unclear response, ask for clarification
            return {
                "state": self.state,
                "recommended_action": "clarify",
                "message": "Response unclear. Please clarify seller's intent."
            }
    
    def _calculate_counter_offer(self, seller_counter: int) -> int:
        """
        Calculate counter offer using decreasing concession strategy.
        
        Args:
            seller_counter: Seller's counter offer
            
        Returns:
            New offer amount
        """
        # Decreasing concession rates per round
        concession_rates = [0.50, 0.40, 0.30, 0.20, 0.15]
        rate = concession_rates[min(self.round - 1, len(concession_rates) - 1)]
        
        gap = seller_counter - self.current_offer
        concession = gap * rate
        new_offer = self.current_offer + concession
        
        # Check for convergence (within 5% of asking)
        if abs(seller_counter - new_offer) < self.asking_price * 0.05:
            # Split the difference
            new_offer = (seller_counter + new_offer) / 2
        
        return int(new_offer)
    
    def _generate_message(self, message_type: str, context: Optional[Dict] = None) -> str:
        """
        Generate negotiation message using LLM.
        
        Args:
            message_type: Type of message (initial_offer, counter_offer, etc.)
            context: Additional context for message generation
            
        Returns:
            Generated message
        """
        if not self.use_llm:
            return self._fallback_message(message_type, context)
        
        try:
            ctx = context or {}
            
            prompts = {
                "initial_offer": f"""Write a friendly, casual message making an initial offer on this item:

Item: {self.listing.title}
Asking Price: {self.listing.price}
Your Offer: ${self.current_offer}

Keep it brief, friendly, and mention you can pick up soon. Don't be apologetic.""",

                "counter_offer": f"""Write a brief counter-offer message:

Item: {self.listing.title}
Seller's Counter: ${ctx.get('seller_counter', 0)}
Your Counter: ${ctx.get('new_offer', 0)}
Gap: ${ctx.get('gap', 0)}

Be friendly but firm. Mention you're close to a deal.""",

                "final_offer": f"""Write a final offer message:

Item: {self.listing.title}
Seller's Counter: ${ctx.get('seller_counter', 0)}
Your Final Offer: ${ctx.get('final_offer', 0)}

Make it clear this is your best and final offer.""",

                "walk_away": f"""Write a polite message declining the deal:

Item: {self.listing.title}

Thank them for their time but decline politely."""
            }
            
            prompt = prompts.get(message_type, prompts["initial_offer"])
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.7,
                system="You are writing marketplace negotiation messages. Be casual, friendly, and brief. 2-3 sentences max. No greetings like 'Hi there'. Start directly.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Message generation failed: {e}")
            return self._fallback_message(message_type, context)
    
    def _analyze_response(self, seller_message: str, seller_counter: Optional[int]) -> Dict:
        """
        Analyze seller's response to determine intent.
        
        Args:
            seller_message: Seller's message
            seller_counter: Seller's counter offer (if any)
            
        Returns:
            Dict with intent and analysis
        """
        if not self.use_llm:
            return self._fallback_analysis(seller_message, seller_counter)
        
        try:
            prompt = f"""Analyze this seller's response to a lowball offer:

Seller's Message: "{seller_message}"
Seller's Counter Price: ${seller_counter if seller_counter else 'None'}

Determine the seller's intent. Return ONLY valid JSON:
{{
  "intent": "<acceptance|rejection|counter|unclear>",
  "confidence": <0-100>,
  "reasoning": "<brief explanation>"
}}

Intent definitions:
- acceptance: Seller agrees to the offer
- rejection: Seller firmly declines
- counter: Seller makes a counter offer or is open to negotiation
- unclear: Cannot determine intent"""

            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.3,
                system="You are analyzing marketplace negotiation responses. Return only valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            text = response.content[0].text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Response analysis failed: {e}")
            return self._fallback_analysis(seller_message, seller_counter)
    
    def _fallback_message(self, message_type: str, context: Optional[Dict] = None) -> str:
        """Fallback messages when LLM unavailable"""
        ctx = context or {}
        
        templates = {
            "initial_offer": f"Hi! Interested in your {self.listing.title}. Would you consider ${self.current_offer}? I can pick up today.",
            "counter_offer": f"Thanks for getting back to me. ${ctx.get('seller_counter', 0)} is a bit high for me. Would ${ctx.get('new_offer', 0)} work?",
            "final_offer": f"${ctx.get('final_offer', 0)} is the best I can do. Let me know if that works.",
            "walk_away": "Thanks for your time, but I'll have to pass at that price. Good luck with the sale!"
        }
        
        return templates.get(message_type, templates["initial_offer"])
    
    def _fallback_analysis(self, seller_message: str, seller_counter: Optional[int]) -> Dict:
        """Fallback analysis when LLM unavailable"""
        message_lower = seller_message.lower()
        
        # Simple keyword matching
        if any(word in message_lower for word in ["yes", "deal", "sold", "ok", "sure"]):
            return {"intent": "acceptance", "confidence": 70}
        elif any(word in message_lower for word in ["no", "not interested", "too low"]):
            return {"intent": "rejection", "confidence": 70}
        elif seller_counter:
            return {"intent": "counter", "confidence": 90}
        else:
            return {"intent": "unclear", "confidence": 50}
    
    def get_state(self) -> Dict:
        """Get current negotiation state"""
        return {
            "state": self.state,
            "asking_price": self.asking_price,
            "current_offer": self.current_offer,
            "max_budget": self.max_budget,
            "round": self.round,
            "messages": self.messages,
            "listing_id": self.listing.id,
            "listing_title": self.listing.title
        }
