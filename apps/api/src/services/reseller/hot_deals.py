"""
Hot deal detection and filtering.
"""

import logging
from typing import List, Optional

from src.models import Listing, Deal, DealRating
from .scorer import DealScorer

logger = logging.getLogger(__name__)


class HotDealDetector:
    """Detect and filter hot deals from listings"""
    
    def __init__(self):
        self.scorer = DealScorer()
        self._trending_cache = None
        self._cache_time = None
    
    def filter_hot_deals(self, deals: List[Deal]) -> List[Deal]:
        """
        Filter deals to return only HOT and GOOD rated deals.
        
        Args:
            deals: List of already-scored Deal objects
            
        Returns:
            List of Deal objects with HOT or GOOD rating, sorted by quality
        """
        # Filter to only HOT and GOOD deals
        hot_deals = [
            d for d in deals 
            if d.deal_rating in [DealRating.HOT, DealRating.GOOD]
        ]
        
        # Sort by rating (HOT first) then by profit estimate
        hot_deals.sort(
            key=lambda d: (
                0 if d.deal_rating == DealRating.HOT else 1,
                -(d.profit_estimate or 0)
            )
        )
        
        return hot_deals
    
    def get_trending_categories(self) -> List[str]:
        """
        Get list of currently trending flip categories using LLM.
        Cached for 1 hour to reduce API calls.
        
        Returns:
            List of category names
        """
        import anthropic
        import os
        from datetime import datetime, timedelta
        
        # Check cache
        if self._trending_cache and self._cache_time:
            if datetime.now() - self._cache_time < timedelta(hours=1):
                return self._trending_cache
        
        # Get from LLM
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return ["electronics", "gaming", "apple products"]  # Fallback
            
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.5,
                system="You are a marketplace resale expert. List currently trending items for flipping.",
                messages=[{
                    "role": "user",
                    "content": "What are the top 8-10 trending items/categories for reselling on Facebook Marketplace right now? Return as a simple comma-separated list."
                }]
            )
            
            text = response.content[0].text.strip()
            categories = [c.strip() for c in text.split(',')]
            
            # Cache results
            self._trending_cache = categories
            self._cache_time = datetime.now()
            
            return categories
            
        except Exception as e:
            logger.error(f"Failed to get trending categories: {e}")
            return ["electronics", "gaming", "apple products"]  # Fallback
    
    def is_trending(self, category: Optional[str]) -> bool:
        """
        Check if a category is currently trending.
        
        Args:
            category: Category name
            
        Returns:
            True if trending
        """
        if not category:
            return False
        
        trending = self.get_trending_categories()
        category_lower = category.lower()
        return any(trend.lower() in category_lower for trend in trending)
    
    def generate_why_standout(self, deal: Deal) -> str:
        """
        Generate enhanced "why it stands out" message.
        This is already done in the scorer, but can be enhanced here.
        
        Args:
            deal: Deal object
            
        Returns:
            Enhanced standout message
        """
        # If already has a good message, return it
        if deal.why_standout:
            # Add trending badge if applicable
            if self.is_trending(deal.category):
                return f"🔥 TRENDING • {deal.why_standout}"
            return deal.why_standout
        
        # Fallback message
        return "Potential deal - review details"
