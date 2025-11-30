"""
Enhanced deal viewer that combines browser automation with eBay analysis.
Integrates with existing scraper and adds intelligent deal scoring.
"""

import re
import logging
from typing import Dict, Optional
from .ebay import DealAnalyzer
from ..models.deal import Deal, DealRating

logger = logging.getLogger(__name__)


class EnhancedDealViewer:
    """
    Sophisticated deal viewer that:
    1. Scrapes Facebook Marketplace listing
    2. Validates price against eBay market data
    3. Scores deal potential with AI
    4. Returns actionable recommendation
    """
    
    def __init__(self):
        try:
            self.analyzer = DealAnalyzer()
        except Exception as e:
            # If eBay credentials not configured, use None
            self.analyzer = None
            logger.warning(f"DealAnalyzer not available: {e}")
    
    def _extract_price(self, price_raw) -> float:
        """Extract numeric price from various formats."""
        if not price_raw:
            return 0
        
        if isinstance(price_raw, (int, float)):
            return float(price_raw)
        
        if isinstance(price_raw, str):
            # Extract numeric value from string like "$1,234" or "1234"
            clean = re.sub(r'[^\d.]', '', price_raw)
            try:
                return float(clean) if clean else 0
            except ValueError:
                return 0
        
        return 0
    
    async def view_and_analyze_deal(
        self,
        listing_data: Dict,
        use_ai: bool = True,
        min_rating: DealRating = DealRating.GOOD
    ) -> Dict:
        """
        View a deal and analyze its potential.
        
        Args:
            listing_data: Dict with title, price, condition, description, url
            use_ai: Whether to use Claude for enhanced analysis
            min_rating: Minimum rating to recommend pursuing
            
        Returns:
            Dict with recommendation, analysis, and listing details
        """
        # Extract listing info
        title = listing_data.get("title", "")
        
        # Get price - try price_value first, then price string
        price = self._extract_price(listing_data.get("price_value"))
        if price == 0:
            price = self._extract_price(listing_data.get("price"))
        
        # Log the price we're using
        logger.info(f"Analyzing deal: {title[:50]}... at ${price:.2f}")
        
        condition = listing_data.get("condition", "USED")
        description = listing_data.get("description", "")
        url = listing_data.get("url", "")
        
        # Analyze deal potential
        if self.analyzer and price > 0:
            analysis = await self.analyzer.analyze_deal(
                listing_title=title,
                listing_price=price,
                listing_condition=condition,
                listing_description=description,
                use_ai=use_ai
            )
        else:
            # Fallback: basic analysis without eBay
            analysis = {
                "deal_rating": DealRating.FAIR,
                "profit_estimate": 0,
                "roi_percent": 0,
                "ebay_avg_price": 0,
                "ebay_median_price": price,
                "confidence": "LOW",
                "reason": "eBay integration not configured or price is zero.",
                "comparable_count": 0,
                "score": 50
            }
        
        # Determine recommendation
        rating = analysis["deal_rating"]
        should_pursue = self._should_pursue(rating, min_rating)
        
        # Calculate negotiation strategy if pursuing
        negotiation_strategy = None
        if should_pursue and price > 0:
            negotiation_strategy = self._calculate_negotiation_strategy(
                asking_price=price,
                ebay_median=analysis["ebay_median_price"],
                profit_estimate=analysis["profit_estimate"]
            )
        
        return {
            "should_pursue": should_pursue,
            "listing": {
                "title": title,
                "price": price,  # Return numeric price
                "price_formatted": f"${price:,.0f}" if price > 0 else "Price not available",
                "condition": condition,
                "url": url,
                "description": description[:200] if description else ""
            },
            "analysis": {
                "rating": rating.value if hasattr(rating, 'value') else str(rating),
                "score": analysis["score"],
                "profit_estimate": analysis["profit_estimate"],
                "roi_percent": analysis["roi_percent"],
                "ebay_avg_price": analysis["ebay_avg_price"],
                "confidence": analysis["confidence"],
                "reason": analysis["reason"]
            },
            "negotiation_strategy": negotiation_strategy,
            "action_items": self._generate_action_items(
                should_pursue=should_pursue,
                rating=rating,
                negotiation_strategy=negotiation_strategy
            )
        }
    
    def _should_pursue(self, rating: DealRating, min_rating: DealRating) -> bool:
        """Determine if deal meets minimum threshold"""
        rating_order = {
            DealRating.HOT: 4,
            DealRating.GOOD: 3,
            DealRating.FAIR: 2,
            DealRating.PASS: 1
        }
        return rating_order.get(rating, 1) >= rating_order.get(min_rating, 2)

    
    def _calculate_negotiation_strategy(
        self,
        asking_price: float,
        ebay_median: float,
        profit_estimate: float
    ) -> Dict:
        """
        Calculate optimal negotiation strategy based on LISTING price.
        
        Strategy:
        - Initial offer: 65% of asking (35% discount)
        - Target price: 80% of asking (20% discount)
        - Walk-away: 90% of asking (10% discount)
        """
        # Ensure we have a valid asking price
        if asking_price <= 0:
            asking_price = ebay_median if ebay_median > 0 else 100
        
        initial_offer = asking_price * 0.65
        target_price = asking_price * 0.80
        walk_away_price = asking_price * 0.90
        
        # Adjust based on market data
        if ebay_median > 0 and asking_price < ebay_median:
            # Already priced below market - be less aggressive
            discount_pct = ((ebay_median - asking_price) / ebay_median) * 100
            if discount_pct > 30:
                initial_offer = asking_price * 0.80
                target_price = asking_price * 0.90
                walk_away_price = asking_price * 0.95
        
        return {
            "initial_offer": round(initial_offer, 2),
            "target_price": round(target_price, 2),
            "walk_away_price": round(walk_away_price, 2),
            "strategy": "aggressive" if profit_estimate > 100 else "moderate",
            "talking_points": [
                f"Market research shows similar items at ${ebay_median:.0f}" if ebay_median > 0 else "Researched comparable items",
                "Can pick up today with cash",
                "Serious buyer, no time wasters"
            ]
        }
    
    def _generate_action_items(
        self,
        should_pursue: bool,
        rating: DealRating,
        negotiation_strategy: Optional[Dict]
    ) -> list:
        """Generate actionable next steps"""
        if not should_pursue:
            return [
                "❌ Skip this listing",
                "Continue searching for better deals"
            ]
        
        actions = []
        
        if rating == DealRating.HOT:
            actions.append("🔥 HOT DEAL - Act fast!")
            actions.append("Contact seller immediately")
        elif rating == DealRating.GOOD:
            actions.append("✅ Good opportunity")
            actions.append("Contact seller within 24 hours")
        else:
            actions.append("📊 Fair deal - proceed with caution")
        
        if negotiation_strategy:
            actions.append(
                f"💰 Start negotiation at ${negotiation_strategy['initial_offer']:.0f}"
            )
            actions.append(
                f"🎯 Target price: ${negotiation_strategy['target_price']:.0f}"
            )
            actions.append(
                f"🚪 Walk away above ${negotiation_strategy['walk_away_price']:.0f}"
            )
        
        actions.append("📸 Request additional photos")
        actions.append("🔍 Verify item authenticity")
        actions.append("📍 Confirm pickup location")
        
        return actions
