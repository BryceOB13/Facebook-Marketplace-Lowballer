"""
Negotiation Strategy Selection

Selects the appropriate negotiation approach based on:
- Deal quality rating
- Listing age (older = more leverage)
- Market conditions
- User preferences
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class StrategyTier(str, Enum):
    """Negotiation aggressiveness tiers."""
    SHREWD = "shrewd"
    MODERATE = "moderate"
    LENIENT = "lenient"
    ACCEPT = "accept"


@dataclass
class NegotiationStrategy:
    """Strategy configuration for a negotiation."""
    tier: StrategyTier
    name: str
    initial_offer_pct: float
    max_increase_per_round: float
    tone_guidance: str
    opening_approach: str
    counter_approach: str
    walk_away_approach: str
    
    def calculate_initial_offer(self, asking_price: float) -> float:
        """Calculate the initial offer amount."""
        return round(asking_price * self.initial_offer_pct, -1)
    
    def calculate_next_offer(
        self, 
        asking_price: float,
        our_last_offer: float,
        seller_last_offer: Optional[float] = None
    ) -> float:
        """Calculate next counter-offer."""
        max_bump = asking_price * self.max_increase_per_round
        
        if seller_last_offer:
            midpoint = (our_last_offer + seller_last_offer) / 2
            new_offer = min(our_last_offer + max_bump, midpoint)
        else:
            new_offer = our_last_offer + (max_bump * 0.5)
        
        return round(new_offer, -1)


# Pre-defined strategies
STRATEGIES = {
    StrategyTier.SHREWD: NegotiationStrategy(
        tier=StrategyTier.SHREWD,
        name="Shrewd Negotiator",
        initial_offer_pct=0.50,
        max_increase_per_round=0.10,
        tone_guidance="Be direct and businesslike. Show you know the market. Don't be rude, but don't be overly friendly either.",
        opening_approach="Start with genuine interest but immediately pivot to price. Make a confident low offer with brief justification.",
        counter_approach="Acknowledge their counter but hold firm initially. Move in small increments. Show you're willing to walk.",
        walk_away_approach="Be polite but clear: 'I appreciate your time, but that's above my budget. If you reconsider, feel free to reach out.'"
    ),
    
    StrategyTier.MODERATE: NegotiationStrategy(
        tier=StrategyTier.MODERATE,
        name="Balanced Negotiator",
        initial_offer_pct=0.70,
        max_increase_per_round=0.08,
        tone_guidance="Be friendly but purposeful. Build light rapport. Be reasonable but don't leave money on the table.",
        opening_approach="Express genuine interest in the item first. Ask a relevant question about condition. Then make a reasonable offer.",
        counter_approach="Thank them for considering and respond positively. Meet them partway but explain your budget constraints.",
        walk_away_approach="Express genuine disappointment: 'I really wanted this one, but it's just a bit more than I can do right now.'"
    ),
    
    StrategyTier.LENIENT: NegotiationStrategy(
        tier=StrategyTier.LENIENT,
        name="Easy-Going Buyer",
        initial_offer_pct=0.85,
        max_increase_per_round=0.05,
        tone_guidance="Be warm and appreciative. Show enthusiasm for what they're selling. Light negotiation is fine but don't push hard.",
        opening_approach="Lead with enthusiasm about the item. Make a soft ask: 'Would you consider...' or 'Any flexibility on price?'",
        counter_approach="Be gracious with counters. Move toward their price quickly. Focus on logistics to close.",
        walk_away_approach="Be kind: 'That's a bit more than I had in mind, but thanks for listing it! Beautiful item.'"
    ),
    
    StrategyTier.ACCEPT: NegotiationStrategy(
        tier=StrategyTier.ACCEPT,
        name="Quick Buyer",
        initial_offer_pct=1.0,
        max_increase_per_round=0.0,
        tone_guidance="Be enthusiastic and ready to buy. No negotiation needed. Focus on logistics.",
        opening_approach="Express excitement and state you want to buy at listed price. Immediately move to logistics.",
        counter_approach="N/A - accepting listed price",
        walk_away_approach="N/A - great deal, just buy it"
    )
}


class StrategySelector:
    """Selects appropriate strategy based on deal signals."""
    
    def select_strategy(
        self,
        asking_price: float,
        market_avg: float,
        deal_rating: str,
        listing_age_days: Optional[int] = None,
        user_override: Optional[str] = None
    ) -> NegotiationStrategy:
        """Select negotiation strategy based on deal quality and signals."""
        # User override takes precedence
        if user_override:
            tier = StrategyTier(user_override.lower())
            return STRATEGIES[tier]
        
        # Calculate discount from market
        discount_pct = (market_avg - asking_price) / market_avg if market_avg > 0 else 0
        
        # Great deals - just buy them
        if deal_rating == "HOT" or discount_pct > 0.40:
            return STRATEGIES[StrategyTier.ACCEPT]
        
        # Determine base tier from deal quality
        if deal_rating == "PASS" or discount_pct < 0.10:
            base_tier = StrategyTier.SHREWD
        elif deal_rating == "FAIR" or discount_pct < 0.20:
            base_tier = StrategyTier.MODERATE
        else:  # GOOD deal
            base_tier = StrategyTier.LENIENT
        
        # Adjust for listing age (older listings = more leverage)
        if listing_age_days and listing_age_days > 14:
            if base_tier == StrategyTier.LENIENT:
                base_tier = StrategyTier.MODERATE
            elif base_tier == StrategyTier.MODERATE:
                base_tier = StrategyTier.SHREWD
        elif listing_age_days and listing_age_days < 2:
            if base_tier == StrategyTier.SHREWD:
                base_tier = StrategyTier.MODERATE
        
        return STRATEGIES[base_tier]
