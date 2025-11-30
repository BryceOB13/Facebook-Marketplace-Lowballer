"""
AI-powered deal analysis using eBay price data and Claude.
Combines market data with intelligent reasoning for deal scoring.
"""

import os
from typing import Dict, List, Optional
import anthropic
from .ebay_client import EbayBrowseClient, EbayItem
from .query_optimizer import EbayQueryOptimizer
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
        self.query_optimizer = EbayQueryOptimizer()
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
        # Optimize the query for eBay search - pass description for better extraction
        optimized = self.query_optimizer.optimize_query(listing_title, listing_description)
        search_query = optimized["primary_query"]
        secondary_queries = optimized.get("secondary_queries", [])
        
        # TRACE: Log query optimization
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"=== DEAL ANALYSIS ===")
        logger.info(f"Original title: {listing_title}")
        logger.info(f"Description preview: {listing_description[:100] if listing_description else 'None'}...")
        logger.info(f"Optimized query: {search_query}")
        logger.info(f"Listing price: ${listing_price:.2f}")
        logger.info(f"Expected eBay filter range: ${listing_price * 0.25:.0f} - ${listing_price * 2.5:.0f}")
        logger.info(f"Secondary queries: {secondary_queries}")
        
        async with self.ebay_client:
            # Get eBay market data for PRIMARY item with reference price for smart filtering
            ebay_stats = await self.ebay_client.get_price_statistics(
                query=search_query,
                condition=listing_condition,
                reference_price=listing_price  # Pass listing price for smart filtering
            )
            
            # Get the actual items found for analysis
            comparable_items = ebay_stats.get("items", [])
            
            # Calculate BUNDLE VALUE by searching for accessories
            bundle_value = ebay_stats.get("median_price", 0)
            accessory_values = []
            
            for accessory in secondary_queries[:3]:  # Limit to 3 accessories
                try:
                    acc_stats = await self.ebay_client.get_price_statistics(
                        query=accessory,
                        condition=listing_condition,
                        reference_price=None  # Don't filter accessories by price
                    )
                    if acc_stats["median_price"] > 0:
                        accessory_values.append({
                            "item": accessory,
                            "value": acc_stats["median_price"]
                        })
                        bundle_value += acc_stats["median_price"]
                except Exception:
                    pass  # Skip failed accessory searches
        
        # Calculate basic metrics using BUNDLE value
        ebay_avg = ebay_stats["avg_price"]
        ebay_median = ebay_stats["median_price"]
        
        # Use bundle value if we found accessories
        total_market_value = bundle_value if bundle_value > ebay_median else ebay_median
        
        if ebay_avg == 0:
            # No market data available
            return {
                "deal_rating": DealRating.PASS,
                "profit_estimate": 0,
                "roi_percent": 0,
                "ebay_avg_price": 0,
                "ebay_median_price": 0,
                "confidence": "LOW",
                "reason": "No comparable eBay listings found",
                "comparable_count": 0,
                "score": 0
            }
        
        # Calculate profit potential using TOTAL bundle value
        profit_analysis = self._calculate_profit(
            purchase_price=listing_price,
            expected_sale_price=total_market_value,
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
                ebay_avg=total_market_value,
                comparable_items=comparable_items[:10]
            )
            
            # Adjust score based on AI insights - clamp AI score to 0-100 first
            ai_score = max(0, min(ai_insights.get("score", 50), 100))
            final_score = max(0, min((base_score * 0.7) + (ai_score * 0.3), 100))
            reason = ai_insights["reasoning"]
        else:
            final_score = max(0, min(base_score, 100))
            # Use dynamic analysis based on actual data
            reason = self._generate_dynamic_analysis(
                listing_title=listing_title,
                listing_price=listing_price,
                ebay_avg=total_market_value,
                ebay_median=ebay_median,
                comparable_items=comparable_items,
                profit_analysis=profit_analysis
            )
        
        # Determine rating (pass profit to ensure negative profit = PASS)
        rating = self._score_to_rating(final_score, profit_analysis["net_profit"])
        
        # Build reason with bundle info if applicable
        if accessory_values:
            bundle_breakdown = ", ".join([f"{a['item']}: ${a['value']:.0f}" for a in accessory_values])
            reason = f"{reason} Bundle includes: {bundle_breakdown}. Total market value: ${total_market_value:.0f}"
        
        return {
            "deal_rating": rating,
            "profit_estimate": profit_analysis["net_profit"],
            "roi_percent": profit_analysis["roi"],
            "ebay_avg_price": total_market_value,  # Use bundle value
            "ebay_median_price": ebay_median,
            "confidence": self._calculate_confidence(ebay_stats["sample_size"]),
            "reason": reason,
            "comparable_count": len(comparable_items),
            "score": round(max(0, min(final_score, 100)), 2),  # Ensure 0-100
            "bundle_value": total_market_value,
            "primary_item_value": ebay_median,
            "accessories": accessory_values
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
        
        # Avoid division by zero for ROI calculation
        investment = purchase_price + purchase_tax
        roi = round((net_profit / investment) * 100, 2) if investment > 0 else 0
        
        return {
            "net_profit": round(net_profit, 2),
            "roi": roi,
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
        
        Returns: Score normalized to 0-100 (never negative)
        """
        # Price discount score (0-100) - clamp to valid range
        if ebay_median > 0:
            discount_pct = ((ebay_median - listing_price) / ebay_median) * 100
        else:
            discount_pct = 0
        discount_score = max(0, min(discount_pct * 2, 100))  # Clamp 0-100
        
        # ROI score (0-100) - clamp to valid range
        roi = profit_analysis["roi"]
        roi_score = max(0, min(roi, 100))  # Clamp 0-100
        
        # Profit score (0-100) - clamp to 0 minimum
        profit = profit_analysis["net_profit"]
        profit_score = max(0, min((profit / 50) * 100, 100))  # $50 profit = 100 points, min 0
        
        # Confidence score based on sample size
        confidence_score = max(0, min((sample_size / 20) * 100, 100))  # 20+ items = 100 points
        
        # Weighted total
        total_score = (
            discount_score * 0.40 +
            roi_score * 0.30 +
            profit_score * 0.20 +
            confidence_score * 0.10
        )
        
        # Final clamp to ensure 0-100 range
        return max(0, min(total_score, 100))
    
    def _score_to_rating(self, score: float, profit: float = 0) -> DealRating:
        """Convert numeric score to rating. Negative profit always results in PASS."""
        # Hard rule: negative profit = PASS, regardless of score
        if profit < 0:
            return DealRating.PASS
        
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
        
        # Format comparable items with actual data
        comparables_text = "\n".join([
            f"- {item.title}: ${item.price:.2f} ({item.condition})"
            for item in comparable_items[:10]  # Show up to 10 comparables
        ]) if comparable_items else "No comparable items found"
        
        prompt = f"""Analyze this Facebook Marketplace deal for resale potential:

LISTING:
Title: {title}
Asking Price: ${price:.2f}
Description: {description[:500] if description else 'No description provided'}

EBAY MARKET DATA:
Average selling price: ${ebay_avg:.2f}
Number of comparable listings: {len(comparable_items)}

COMPARABLE EBAY LISTINGS:
{comparables_text}

Based on the ACTUAL market data above, assess this deal on a 0-100 scale.

Consider:
1. Price comparison: Is ${price:.2f} a good deal compared to the ${ebay_avg:.2f} eBay average?
2. What the listing title suggests about condition/completeness
3. Any red flags or concerns from the comparable listings

IMPORTANT: Your analysis MUST reference the actual prices shown above. Do not make up numbers.

Respond in JSON format:
{{"score": <0-100>, "reasoning": "<2-3 sentence analysis referencing actual prices>"}}"""

        try:
            response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=250,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result = json.loads(response.content[0].text)
            return result
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return {"score": 50, "reasoning": "AI analysis error"}
    
    def _generate_dynamic_analysis(
        self,
        listing_title: str,
        listing_price: float,
        ebay_avg: float,
        ebay_median: float,
        comparable_items: List[EbayItem],
        profit_analysis: Dict
    ) -> str:
        """Generate analysis text based on actual market data"""
        profit = profit_analysis["net_profit"]
        roi = profit_analysis["roi"]
        
        # Calculate discount percentage
        if ebay_avg > 0:
            discount_pct = ((ebay_avg - listing_price) / ebay_avg) * 100
        else:
            discount_pct = 0
        
        # Build analysis based on actual data
        parts = []
        
        # Price comparison
        if listing_price < ebay_avg:
            parts.append(f"At ${listing_price:.0f}, this is {abs(discount_pct):.0f}% below the eBay average of ${ebay_avg:.0f}.")
        elif listing_price > ebay_avg:
            parts.append(f"At ${listing_price:.0f}, this is {abs(discount_pct):.0f}% above the eBay average of ${ebay_avg:.0f}.")
        else:
            parts.append(f"At ${listing_price:.0f}, this matches the eBay average price.")
        
        # Profit assessment
        if profit > 100:
            parts.append(f"Strong profit potential of ${profit:.0f} ({roi:.0f}% ROI) after fees.")
        elif profit > 0:
            parts.append(f"Modest profit potential of ${profit:.0f} ({roi:.0f}% ROI) after fees.")
        else:
            parts.append(f"Negative margin of ${abs(profit):.0f} - would lose money on resale.")
        
        # Comparable items insight
        if comparable_items:
            prices = [item.price for item in comparable_items[:5]]
            if prices:
                price_range = f"${min(prices):.0f}-${max(prices):.0f}"
                parts.append(f"Similar items on eBay are selling for {price_range}.")
        
        # Title-based observations
        title_lower = listing_title.lower()
        if "not included" in title_lower or "body only" in title_lower:
            parts.append("Note: Listing indicates missing components which may affect resale value.")
        elif "bundle" in title_lower or "kit" in title_lower:
            parts.append("Bundle listing - individual items may have different resale values.")
        
        return " ".join(parts)
