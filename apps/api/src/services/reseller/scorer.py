"""
Deal scoring algorithm - Agentic workflow using Claude Haiku.
Uses LLM to evaluate market value and deal quality.
"""

import logging
import os
import json
from typing import Optional, Dict
import anthropic

from src.models import Listing, Deal, DealRating

logger = logging.getLogger(__name__)


class DealScorer:
    """
    Score deals using Claude Haiku for intelligent market analysis.
    Cost-optimized: ~$0.002 per listing evaluation.
    """
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.use_llm = self.client is not None
    
    def score_listing(self, listing: Listing) -> Deal:
        """
        Score a listing using LLM-based market analysis.
        
        Args:
            listing: Listing to score
            
        Returns:
            Deal with scoring data
        """
        if not self.use_llm:
            logger.warning("LLM not available, returning neutral score")
            return self._create_neutral_deal(listing)
        
        try:
            # Get LLM evaluation
            evaluation = self._evaluate_with_llm(listing)
            
            # Parse evaluation results
            rating = self._parse_rating(evaluation.get('rating', 'FAIR'))
            
            # Create Deal object - merge listing data with evaluation
            listing_data = listing.model_dump()
            listing_data.update({
                'ebay_avg_price': evaluation.get('market_value'),
                'profit_estimate': evaluation.get('profit_estimate'),
                'roi_percent': evaluation.get('roi_percent'),
                'deal_rating': rating,
                'is_new': True,
                'price_changed': False,
                'old_price': None,
                'why_standout': evaluation.get('why_standout', 'Review details'),
                'category': evaluation.get('category'),
                'match_score': evaluation.get('score', 50) / 100.0
            })
            return Deal(**listing_data)
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return self._create_neutral_deal(listing)
    
    def _evaluate_with_llm(self, listing: Listing) -> Dict:
        """
        Use Claude Haiku to evaluate listing and estimate market value.
        Cost: ~$0.002 per evaluation (Haiku is $0.25/MTok input, $1.25/MTok output)
        """
        prompt = f"""Evaluate this Facebook Marketplace listing as a potential resale opportunity:

Title: {listing.title}
Price: {listing.price}
Location: {listing.location or 'Not specified'}

Analyze:
1. What is the typical market value for this item? (used/resale price)
2. Is this a good deal for reselling?
3. What category does this belong to?
4. Estimated profit after 5% Facebook fee and 6.25% purchase tax
5. Why does this stand out (or not)?

Return ONLY valid JSON:
{{
  "market_value": <typical resale price as number>,
  "category": "<item category>",
  "score": <0-100 deal quality score>,
  "rating": "<HOT|GOOD|FAIR|PASS>",
  "profit_estimate": <estimated profit as number>,
  "roi_percent": <ROI percentage as number>,
  "why_standout": "<brief explanation>"
}}

Be realistic about market values. Consider condition, demand, and resale velocity."""

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.3,
                system="You are a marketplace resale expert. Evaluate deals objectively based on real market data. Return only valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            text = response.content[0].text.strip()
            
            # Extract JSON if wrapped in markdown
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            
            evaluation = json.loads(text)
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
            raise
    
    def _parse_rating(self, rating_str: str) -> DealRating:
        """Convert string rating to enum"""
        rating_map = {
            'HOT': DealRating.HOT,
            'GOOD': DealRating.GOOD,
            'FAIR': DealRating.FAIR,
            'PASS': DealRating.PASS
        }
        return rating_map.get(rating_str.upper(), DealRating.FAIR)
    
    def _create_neutral_deal(self, listing: Listing) -> Deal:
        """Create a neutral deal when LLM is unavailable"""
        listing_data = listing.model_dump()
        listing_data.update({
            'ebay_avg_price': None,
            'profit_estimate': None,
            'roi_percent': None,
            'deal_rating': DealRating.FAIR,
            'is_new': True,
            'price_changed': False,
            'old_price': None,
            'why_standout': "LLM evaluation unavailable",
            'category': None,
            'match_score': 0.5
        })
        return Deal(**listing_data)

