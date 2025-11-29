"""
AI-powered deal analysis using eBay price data and Claude.
Combines market data with intelligent reasoning for deal scoring.
"""

import os
from typing import Dict, List, Optional
import anthropic
from .ebay_client import EbayBrowseClient, EbayItem
from ...models.deal import Deal, DealRating


class DealAnalyzer:
    """
    Sophisticated deal analyzer that combines:
    1. eBay market data for price validation
    2. Claude Haiku for intelligent deal assessment
    3. Multi-factor scoring algorithm
    """
    
    # Platform fee structures
    PLATFORM_FEES = {
        'ebay': {
            'base_rate': 0.1325,  # 13.25% final value fee
            'per_order': 0.40,
            'regulatory': 0.0035
        },
        'facebook': {
            'rate': 0.05,
            'flat_threshold': 8.00
        }
    }
    
    def __init__(self):
        self.ebay_client = EbayBrowseClient()
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude = anthropic.Anthropic(api_key=anthropic_key) if anthropic_key else None
    
    async def analyze_deal(
        self,
        listing_title: str,
        listing_price: float,
        listing_condition: str = "USED",
        listing_description: Optional[str] = None,
        use_ai: bool = True
    ) -> Dict:
        """
        Comprehensive deal analysis combining market data and AI reasoning.
        
        Args:
            listing_title: Facebook Marketplace listing title
            listing_price: Asking price
            listing_condition: Item condition
            listing_description: Full description (optional)
            use_ai: Whether to use Claude for enhanced analysis
            
        Returns:
            Dict with deal_rating, profit_estimate, roi_percent, ebay_avg_price, etc.
        """
        async with self.ebay_client:
            # Get eBay market data
            ebay_stats = await self.ebay_client.get_price_statistics(
                query=listing_title,
                condition=listing_condition
            )
            
            comparable_items = await self.ebay_client.find_comparable_items(
                title=listing_title,
                price=listing_price,
                condition=listing_condition
            )
        
        # Calculate basic metrics
        ebay_avg = ebay_stats["avg_price"]
        ebay_median = ebay_stats["median_price"]
        
        if ebay_avg == 0:
            # No market data available
            return {
                "deal_rating": DealRating.PASS,
                "profit_estimate": 0,
                "roi_percent": 0,
                "ebay_avg_price": 0,
                "confidence": "LOW",
                "reason": "No comparable eBay listings found"
            }
        
        # Calculate profit potential
        profit_analysis = self._calculate_profit(
            purchase_price=listing_price,
            expected_sale_price=ebay_median,
            platform="ebay"
        )
        
        # Base scoring
        base_score = self._calculate_base_score(
            listing_price=listing_price,
            ebay_avg=ebay_avg,
            ebay_median=ebay_median,
            profit_analysis=profit_analysis,
            sample_size=ebay_stats["sample_size"]
        )
        
        # AI-enhanced analysis if enabled
        if use_ai and self.claude and listing_description:
            ai_insights = await self._get_ai_insights(
                title=listing_title,
                description=listing_description,
                price=listing_price,
                ebay_avg=ebay_avg,
                comparable_items=comparable_items[:5]
            )
            
            # Adjust score based on AI insights
            final_score = (base_score * 0.7) + (ai_insights["score"] * 0.3)
            reason = ai_insights["reasoning"]
        else:
            final_score = base_score
            reason = self._generate_basic_reason(listing_price, ebay_avg, profit_analysis)
        
        # Determine rating
        rating = self._score_to_rating(final_score)
        
        return {
            "deal_rating": rating,
            "profit_estimate": profit_analysis["net_profit"],
            "roi_percent": profit_analysis["roi"],
            "ebay_avg_price": ebay_avg,
            "ebay_median_price": ebay_median,
            "confidence": self._calculate_confidence(ebay_stats["sample_size"]),
            "reason": reason,
            "comparable_count": len(comparable_items),
            "score": round(final_score, 2)
        }
    
    def _calculate_profit(
        self,
        purchase_price: float,
        expected_sale_price: float,
        platform: str = "ebay",
        shipping_cost: float = 10.0,
        tax_rate: float = 0.0625
    ) -> Dict[str, float]:
        """Calculate net profit and ROI"""
        fees = self.PLATFORM_FEES[platform]
        
        if platform == 'ebay':
            platform_fee = (
                expected_sale_price * fees['base_rate'] +
                fees['per_order'] +
                expected_sale_price * fees['regulatory']
            )
        elif platform == 'facebook':
            platform_fee = max(0.40, expected_sale_price * fees['rate'])
        
        purchase_tax = purchase_price * tax_rate
        total_cost = purchase_price + purchase_tax + platform_fee + shipping_cost
        net_profit = expected_sale_price - total_cost
        
        return {
            "net_profit": round(net_profit, 2),
            "roi": round((net_profit / (purchase_price + purchase_tax)) * 100, 2),
            "break_even": round(total_cost, 2),
            "platform_fee": round(platform_fee, 2)
        }
    
    def _calculate_base_score(
        self,
        listing_price: float,
        ebay_avg: float,
        ebay_median: float,
        profit_analysis: Dict,
        sample_size: int
    ) -> float:
        """
        Multi-factor scoring algorithm.
        
        Factors:
        - Price discount vs market (40%)
        - ROI potential (30%)
        - Absolute profit (20%)
        - Market data confidence (10%)
        """
        # Price discount score (0-100)
        discount_pct = ((ebay_median - listing_price) / ebay_median) * 100
        discount_score = min(discount_pct * 2, 100)  # 50% discount = 100 points
        
        # ROI score (0-100)
        roi = profit_analysis["roi"]
        roi_score = min(roi, 100)  # 100% ROI = 100 points
        
        # Profit score (0-100)
        profit = profit_analysis["net_profit"]
        profit_score = min((profit / 50) * 100, 100)  # $50 profit = 100 points
        
        # Confidence score based on sample size
        confidence_score = min((sample_size / 20) * 100, 100)  # 20+ items = 100 points
        
        # Weighted total
        total_score = (
            discount_score * 0.40 +
            roi_score * 0.30 +
            profit_score * 0.20 +
            confidence_score * 0.10
        )
        
        return total_score
    
    def _score_to_rating(self, score: float) -> DealRating:
        """Convert numeric score to rating"""
        if score >= 80:
            return DealRating.HOT
        elif score >= 60:
            return DealRating.GOOD
        elif score >= 40:
            return DealRating.FAIR
        else:
            return DealRating.PASS
    
    def _calculate_confidence(self, sample_size: int) -> str:
        """Calculate confidence level based on sample size"""
        if sample_size >= 20:
            return "HIGH"
        elif sample_size >= 10:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_basic_reason(
        self,
        listing_price: float,
        ebay_avg: float,
        profit_analysis: Dict
    ) -> str:
        """Generate human-readable reason without AI"""
        discount_pct = ((ebay_avg - listing_price) / ebay_avg) * 100
        profit = profit_analysis["net_profit"]
        roi = profit_analysis["roi"]
        
        if profit > 50 and roi > 50:
            return f"Strong deal: {discount_pct:.0f}% below market, ${profit:.0f} profit potential ({roi:.0f}% ROI)"
        elif profit > 20:
            return f"Good opportunity: {discount_pct:.0f}% discount, ${profit:.0f} estimated profit"
        elif discount_pct > 20:
            return f"Fair price: {discount_pct:.0f}% below average but modest profit margin"
        else:
            return f"Limited upside: Only {discount_pct:.0f}% below market average"
    
    async def _get_ai_insights(
        self,
        title: str,
        description: str,
        price: float,
        ebay_avg: float,
        comparable_items: List[EbayItem]
    ) -> Dict:
        """
        Use Claude Haiku for intelligent deal assessment.
        Cost: ~$0.001 per analysis
        """
        if not self.claude:
            return {"score": 50, "reasoning": "AI analysis unavailable"}
        
        # Format comparable items
        comparables_text = "\n".join([
            f"- {item.title}: ${item.price} ({item.condition})"
            for item in comparable_items
        ])
        
        prompt = f"""Analyze this Facebook Marketplace deal for resale potential:

LISTING:
Title: {title}
Price: ${price}
Description: {description[:500]}

MARKET DATA:
eBay Average: ${ebay_avg}
Comparable eBay Listings:
{comparables_text}

Assess this deal on a 0-100 scale considering:
1. Price vs market value
2. Item condition/authenticity concerns from description
3. Resale demand indicators
4. Hidden costs or red flags

Respond in JSON format:
{{"score": <0-100>, "reasoning": "<2-3 sentence explanation>"}}"""

        try:
            response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result = json.loads(response.content[0].text)
            return result
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return {"score": 50, "reasoning": "AI analysis error"}
