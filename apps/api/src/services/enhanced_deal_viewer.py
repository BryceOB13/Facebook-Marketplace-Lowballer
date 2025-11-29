"""
Enhanced deal viewer that combines browser automation with eBay analysis.
Integrates with existing scraper and adds intelligent deal scoring.
"""

from typing import Dict, Optional
from .ebay import DealAnalyzer
from ..models.deal import Deal, DealRating


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
            # We'll provide basic analysis without eBay data
            self.analyzer = None
    
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
            min_rating: Minimum rating to recommend pursuing (HOT, GOOD, FAIR, PASS)
            
        Returns:
            Dict with recommendation, analysis, and listing details
        """
        # Extract listing info
        title = listing_data.get("title", "")
        price_raw = listing_data.get("price_value") or listing_data.get("price", 0)
        
        # Ensure price is a float
        if isinstance(price_raw, str):
            import re
            price = float(re.sub(r'[^\d.]', '', price_raw)) if price_raw else 0
        else:
            price = float(price_raw) if price_raw else 0
        
        condition = listing_data.get("condition", "USED")
        description = listing_data.get("description", "")
        url = listing_data.get("url", "")
        
        # Analyze deal potential
        if self.analyzer:
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
                "reason": "eBay integration not configured. Add EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to .env for market analysis.",
                "comparable_count": 0,
                "score": 50
            }
        
        # Determine recommendation
        rating = analysis["deal_rating"]
        should_pursue = self._should_pursue(rating, min_rating)
        
        # Calculate negotiation strategy if pursuing
        negotiation_strategy = None
        if should_pursue:
            negotiation_strategy = self._calculate_negotiation_strategy(
                asking_price=price,
                ebay_median=analysis["ebay_median_price"],
                profit_estimate=analysis["profit_estimate"]
            )
        
        return {
            "should_pursue": should_pursue,
            "listing": {
                "title": title,
                "price": price,
                "condition": condition,
                "url": url,
                "description": description[:200]  # Truncate for display
            },
            "analysis": {
                "rating": rating.value,
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
    
    def _should_pursue(
        self,
        rating: DealRating,
        min_rating: DealRating
    ) -> bool:
        """Determine if deal meets minimum threshold"""
        rating_order = {
            DealRating.HOT: 4,
            DealRating.GOOD: 3,
            DealRating.FAIR: 2,
            DealRating.PASS: 1
        }
        return rating_order[rating] >= rating_order[min_rating]
    
    def _calculate_negotiation_strategy(
        self,
        asking_price: float,
        ebay_median: float,
        profit_estimate: float
    ) -> Dict:
        """
        Calculate optimal negotiation strategy.
        
        Strategy:
        - Initial offer: 65% of asking (35% discount)
        - Target price: 80% of asking (20% discount)
        - Walk-away: 90% of asking (10% discount)
        """
        # Ensure asking_price is a float
        if isinstance(asking_price, str):
            # Extract numeric value from string like "$1,234"
            import re
            asking_price = float(re.sub(r'[^\d.]', '', asking_price))
        
        initial_offer = asking_price * 0.65
        target_price = asking_price * 0.80
        walk_away_price = asking_price * 0.90
        
        # Adjust based on market data
        if ebay_median > 0:
            # If already priced well below market, be more aggressive
            discount_pct = ((ebay_median - asking_price) / ebay_median) * 100
            if discount_pct > 30:
                initial_offer = asking_price * 0.75  # Less aggressive
                target_price = asking_price * 0.85
        
        return {
            "initial_offer": round(initial_offer, 2),
            "target_price": round(target_price, 2),
            "walk_away_price": round(walk_away_price, 2),
            "strategy": "aggressive" if profit_estimate > 100 else "moderate",
            "talking_points": [
                f"Market research shows similar items at ${ebay_median:.0f}",
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


# Example usage
async def example_usage():
    """Example of how to use EnhancedDealViewer"""
    viewer = EnhancedDealViewer()
    
    # Simulated listing data (would come from scraper)
    listing = {
        "title": "iPhone 13 Pro 256GB Unlocked",
        "price": 450,
        "condition": "USED",
        "description": "Excellent condition, no scratches, includes original box and charger. Battery health 95%. Unlocked for all carriers.",
        "url": "https://facebook.com/marketplace/item/123456"
    }
    
    # Analyze the deal
    result = await viewer.view_and_analyze_deal(
        listing_data=listing,
        use_ai=True,
        min_rating=DealRating.GOOD
    )
    
    # Display results
    if result["should_pursue"]:
        print(f"✅ PURSUE THIS DEAL")
        print(f"Rating: {result['analysis']['rating']}")
        print(f"Profit: ${result['analysis']['profit_estimate']:.2f}")
        print(f"ROI: {result['analysis']['roi_percent']:.1f}%")
        print(f"\nReason: {result['analysis']['reason']}")
        print(f"\nAction Items:")
        for action in result["action_items"]:
            print(f"  {action}")
    else:
        print("❌ Skip this deal")
