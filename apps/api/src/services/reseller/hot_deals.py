"""
Hot deal detection and filtering.
"""

import logging
from typing import List

from src.models import Listing, Deal, DealRating
from .scorer import DealScorer

logger = logging.getLogger(__name__)


class HotDealDetector:
    """Detect and filter hot deals from listings"""
    
    # Currently trending categories (manually curated)
    TRENDING_CATEGORIES = [
        "iphone 15",
        "ps5",
        "nintendo switch",
        "macbook air m2",
        "airpods pro",
        "xbox series x",
        "ipad pro",
        "gaming laptop",
    ]
    
    def __init__(self):
        self.scorer = DealScorer()
    
    def filter_hot_deals(self, listings: List[Listing]) -> List[Deal]:
        """
        Score all listings and return only HOT and GOOD deals.
        
        Args:
            listings: List of listings to score
            
        Returns:
            List of Deal objects with HOT or GOOD rating
        """
        deals = []
        
        for listing in listings:
            try:
                deal = self.scorer.score_listing(listing)
                
                # Only include HOT and GOOD deals
                if deal.deal_rating in [DealRating.HOT, DealRating.GOOD]:
                    deals.append(deal)
                    
            except Exception as e:
                logger.error(f"Failed to score listing {listing.id}: {e}")
                continue
        
        # Sort by rating (HOT first) then by profit estimate
        deals.sort(
            key=lambda d: (
                0 if d.deal_rating == DealRating.HOT else 1,
                -(d.profit_estimate or 0)
            )
        )
        
        return deals
    
    def get_trending_categories(self) -> List[str]:
        """
        Get list of currently trending flip categories.
        
        Returns:
            List of category names
        """
        return self.TRENDING_CATEGORIES.copy()
    
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
        
        category_lower = category.lower()
        return any(trend in category_lower for trend in self.TRENDING_CATEGORIES)
    
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
