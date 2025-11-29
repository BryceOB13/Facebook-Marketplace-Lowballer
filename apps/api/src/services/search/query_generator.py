"""
Query variation generator - Uses Claude Haiku for intelligent query expansion.
Generates multiple search variations to maximize coverage.
"""

import re
import os
from typing import List, Set
import anthropic


class QueryGenerator:
    """Generate query variations using Claude Haiku (cost-optimized)"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.use_llm = self.client is not None
    
    # Category keywords
    CATEGORIES = {
        "electronics": ["laptop", "phone", "tv", "tablet", "camera", "headphones", "speaker"],
        "furniture": ["couch", "desk", "chair", "table", "bed", "dresser"],
        "vehicles": ["car", "truck", "motorcycle", "bike", "scooter"],
        "appliances": ["fridge", "washer", "dryer", "microwave", "dishwasher"],
        "gaming": ["ps5", "xbox", "nintendo", "switch", "playstation", "console"],
        "sports": ["bike", "treadmill", "weights", "golf", "tennis"],
    }
    
    def generate_variations(self, query: str) -> List[str]:
        """
        Generate 3-5 query variations using Claude Haiku.
        
        Args:
            query: Original search query
            
        Returns:
            List of query variations (including original)
        """
        # Always start with original
        variations = [query.strip()]
        
        # Use LLM to generate variations
        if self.use_llm:
            llm_variations = self._generate_with_llm(query)
            for v in llm_variations:
                if v not in variations and len(variations) < 5:
                    variations.append(v)
        
        # If LLM failed or didn't generate enough, add simple fallbacks
        if len(variations) < 3:
            # Just add lowercase and title case versions
            lower = query.lower()
            if lower not in variations:
                variations.append(lower)
            
            title = query.title()
            if title not in variations and len(variations) < 5:
                variations.append(title)
        
        return variations[:5]
    
    def _generate_with_llm(self, query: str) -> List[str]:
        """
        Use Claude Haiku to generate intelligent query variations.
        Cost: ~$0.001 per query (very cheap)
        """
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.3,
                system="""You are a Facebook Marketplace search expert. Generate 4 alternative search queries that would find the same or similar items.

CRITICAL RULES:
- Keep brand names EXACTLY as written (iPhone stays iPhone, not ismartphone)
- Keep model numbers EXACTLY as written (15 stays 15, not 13)
- Only make small variations: add brand prefix, try plural/singular, reorder words slightly
- Each query MUST be a real, sensible search term someone would actually type
- Return ONLY the queries, one per line, nothing else

Examples:
Input: "iPhone 15"
Output:
Apple iPhone 15
iPhone 15 Pro
iphone 15
iPhone fifteen

Input: "gaming laptop"
Output:
gaming laptop
laptop for gaming
gaming laptops
gaming notebook""",
                messages=[{
                    "role": "user",
                    "content": query
                }]
            )
            
            # Parse response - be strict
            text = response.content[0].text.strip()
            variations = []
            
            for line in text.split('\n'):
                clean = line.strip().strip('-').strip('*').strip().strip('1234567890.').strip()
                if clean and len(clean) > 2:
                    # Basic validation: must share at least one word with original
                    if self._shares_words(query, clean):
                        variations.append(clean)
            
            return variations
        except Exception as e:
            print(f"LLM query generation failed: {e}")
            return []
    
    def _shares_words(self, original: str, variation: str) -> bool:
        """Check if variation shares words with original"""
        original_words = set(original.lower().split())
        variation_words = set(variation.lower().split())
        
        # Must share at least one word
        return len(original_words & variation_words) > 0

    def get_category_keywords(self, query: str) -> List[str]:
        """
        Map query to Facebook Marketplace categories.
        
        Args:
            query: Search query
            
        Returns:
            List of matching category keywords
        """
        query_lower = query.lower()
        matching_categories = []
        
        for category, keywords in self.CATEGORIES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    matching_categories.append(category)
                    break
        
        return matching_categories or ["general"]
