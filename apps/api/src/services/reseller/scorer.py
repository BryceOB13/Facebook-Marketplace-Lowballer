"""
Deal scoring algorithm - LOCAL ONLY for MVP.
Uses hardcoded reference prices for common flip items.
"""

import logging
from typing import Optional, Dict
from difflib import SequenceMatcher

from src.models import Listing, Deal, DealRating

logger = logging.getLogger(__name__)


class DealScorer:
    """
    Score deals based on local reference prices.
    No external API calls - all data is hardcoded.
    """
    
    # Hardcoded reference prices for common flip categories
    # Format: "search term": {"low": min_price, "avg": average, "high": max_price}
    REFERENCE_PRICES = {
        # Apple Products
        "iphone 13": {"low": 350, "avg": 450, "high": 550},
        "iphone 14": {"low": 450, "avg": 550, "high": 700},
        "iphone 15": {"low": 600, "avg": 750, "high": 900},
        "macbook air m1": {"low": 600, "avg": 750, "high": 900},
        "macbook air m2": {"low": 800, "avg": 950, "high": 1100},
        "macbook pro m1": {"low": 800, "avg": 1000, "high": 1200},
        "macbook pro m2": {"low": 1200, "avg": 1500, "high": 1800},
        "ipad air": {"low": 350, "avg": 450, "high": 550},
        "ipad pro": {"low": 600, "avg": 800, "high": 1000},
        "airpods pro": {"low": 150, "avg": 180, "high": 220},
        "apple watch": {"low": 200, "avg": 300, "high": 400},
        
        # Gaming Consoles
        "ps5": {"low": 350, "avg": 400, "high": 450},
        "ps4": {"low": 150, "avg": 200, "high": 250},
        "xbox series x": {"low": 350, "avg": 400, "high": 450},
        "xbox series s": {"low": 200, "avg": 250, "high": 300},
        "nintendo switch": {"low": 180, "avg": 220, "high": 280},
        "nintendo switch oled": {"low": 250, "avg": 300, "high": 350},
        
        # Laptops
        "dell xps": {"low": 600, "avg": 800, "high": 1000},
        "thinkpad": {"low": 400, "avg": 600, "high": 800},
        "surface laptop": {"low": 500, "avg": 700, "high": 900},
        "gaming laptop": {"low": 700, "avg": 1000, "high": 1500},
        
        # Audio
        "bose headphones": {"low": 150, "avg": 200, "high": 250},
        "sony headphones": {"low": 150, "avg": 200, "high": 250},
        "beats": {"low": 100, "avg": 150, "high": 200},
        "airpods": {"low": 80, "avg": 120, "high": 150},
        
        # Cameras
        "canon camera": {"low": 300, "avg": 500, "high": 800},
        "nikon camera": {"low": 300, "avg": 500, "high": 800},
        "sony camera": {"low": 400, "avg": 600, "high": 1000},
        "gopro": {"low": 150, "avg": 250, "high": 350},
        
        # Furniture
        "herman miller chair": {"low": 400, "avg": 600, "high": 800},
        "standing desk": {"low": 200, "avg": 350, "high": 500},
        "gaming chair": {"low": 100, "avg": 200, "high": 300},
    }
    
    # Scoring weights
    WEIGHTS = {
        'price_vs_reference': 0.40,
        'title_quality': 0.20,
        'has_images': 0.15,
        'location': 0.15,
        'listing_age': 0.10,
    }
    
    def score_listing(self, listing: Listing) -> Deal:
        """
        Score a listing and convert to Deal.
        
        Args:
            listing: Listing to score
            
        Returns:
            Deal with scoring data
        """
        # Find matching reference price
        category, reference = self._match_to_reference(listing.title)
        
        # Calculate scores
        scores = self._calculate_scores(listing, reference)
        
        # Calculate total score (0-100)
        total_score = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        
        # Determine rating
        rating = self._get_rating(total_score)
        
        # Calculate profit estimate
        profit_data = self._calculate_profit(listing, reference) if reference else None
        
        # Generate "why it stands out" message
        why_standout = self._generate_why_standout(listing, reference, scores, profit_data)
        
        # Create Deal object
        return Deal(
            **listing.model_dump(),
            ebay_avg_price=reference['avg'] if reference else None,
            profit_estimate=profit_data['net_profit'] if profit_data else None,
            roi_percent=profit_data['roi'] if profit_data else None,
            deal_rating=rating,
            is_new=True,
            price_changed=False,
            old_price=None,
            why_standout=why_standout,
            category=category,
            match_score=total_score / 100.0
        )
    
    def _match_to_reference(self, title: str) -> tuple[Optional[str], Optional[Dict]]:
        """
        Match listing title to reference prices using fuzzy matching.
        
        Returns:
            Tuple of (category, reference_dict) or (None, None)
        """
        title_lower = title.lower()
        best_match = None
        best_score = 0.0
        best_category = None
        
        for category, reference in self.REFERENCE_PRICES.items():
            # Calculate similarity score
            score = SequenceMatcher(None, category, title_lower).ratio()
            
            # Also check if category keywords are in title
            if category in title_lower:
                score += 0.3
            
            if score > best_score:
                best_score = score
                best_match = reference
                best_category = category
        
        # Only return if match is good enough
        if best_score > 0.4:
            return best_category, best_match
        
        return None, None
    
    def _calculate_scores(self, listing: Listing, reference: Optional[Dict]) -> Dict[str, float]:
        """Calculate individual scoring components (0-100 each)"""
        scores = {}
        
        # Price vs reference (40% weight)
        if reference and listing.price_value:
            price_ratio = listing.price_value / reference['avg']
            if price_ratio < 0.5:
                scores['price_vs_reference'] = 100  # 50%+ below average
            elif price_ratio < 0.7:
                scores['price_vs_reference'] = 80   # 30-50% below
            elif price_ratio < 0.85:
                scores['price_vs_reference'] = 60   # 15-30% below
            else:
                scores['price_vs_reference'] = 30   # Near or above average
        else:
            scores['price_vs_reference'] = 50  # Unknown, neutral score
        
        # Title quality (20% weight)
        title_len = len(listing.title)
        if title_len > 30 and title_len < 100:
            scores['title_quality'] = 100  # Good descriptive title
        elif title_len > 15:
            scores['title_quality'] = 70   # Decent title
        else:
            scores['title_quality'] = 40   # Short/vague title
        
        # Has images (15% weight)
        scores['has_images'] = 100 if listing.image_url else 30
        
        # Location (15% weight) - prefer local
        if listing.location:
            # Check if location mentions "miles" (nearby)
            if 'mile' in listing.location.lower():
                scores['location'] = 100
            else:
                scores['location'] = 70
        else:
            scores['location'] = 50
        
        # Listing age (10% weight) - assume recent for now
        scores['listing_age'] = 80  # Default to recent
        
        return scores
    
    def _get_rating(self, score: float) -> DealRating:
        """Convert numeric score to rating"""
        if score >= 80:
            return DealRating.HOT
        elif score >= 60:
            return DealRating.GOOD
        elif score >= 40:
            return DealRating.FAIR
        else:
            return DealRating.PASS
    
    def _calculate_profit(self, listing: Listing, reference: Dict) -> Optional[Dict]:
        """
        Calculate potential profit after fees.
        
        Args:
            listing: Listing with price
            reference: Reference price data
            
        Returns:
            Dict with net_profit, roi, break_even
        """
        if not listing.price_value:
            return None
        
        buy_price = listing.price_value
        sell_price = reference['avg']
        
        # Facebook Marketplace fee: 5% or $0.40 (whichever is greater)
        fb_fee = max(0.40, sell_price * 0.05)
        
        # Assume local pickup (no shipping)
        shipping_cost = 0
        
        # Sales tax on purchase (estimate 6.25%)
        purchase_tax = buy_price * 0.0625
        
        total_cost = buy_price + purchase_tax + fb_fee + shipping_cost
        net_profit = sell_price - total_cost
        roi = (net_profit / (buy_price + purchase_tax)) * 100
        
        return {
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 2),
            'break_even': round(total_cost, 2)
        }
    
    def _generate_why_standout(
        self,
        listing: Listing,
        reference: Optional[Dict],
        scores: Dict[str, float],
        profit_data: Optional[Dict]
    ) -> str:
        """Generate human-readable explanation of why deal stands out"""
        reasons = []
        
        if reference and listing.price_value:
            percent_below = ((reference['avg'] - listing.price_value) / reference['avg']) * 100
            if percent_below > 50:
                reasons.append(f"{int(percent_below)}% below typical price")
            elif percent_below > 30:
                reasons.append(f"{int(percent_below)}% below market value")
            elif percent_below > 15:
                reasons.append(f"Priced ${int(reference['avg'] - listing.price_value)} under average")
        
        if profit_data and profit_data['net_profit'] > 100:
            reasons.append(f"Est. ${int(profit_data['net_profit'])} profit")
        
        if profit_data and profit_data['roi'] > 50:
            reasons.append(f"{int(profit_data['roi'])}% ROI potential")
        
        if scores.get('has_images', 0) > 80:
            reasons.append("Has photos")
        
        if scores.get('location', 0) > 80:
            reasons.append("Local pickup available")
        
        if not reasons:
            reasons.append("Potential deal - review details")
        
        return " • ".join(reasons)
