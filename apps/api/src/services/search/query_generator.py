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
    
    # Common marketplace synonyms
    SYNONYMS = {
        "laptop": ["notebook", "macbook", "chromebook"],
        "phone": ["iphone", "smartphone", "mobile"],
        "tv": ["television", "smart tv", "4k tv"],
        "bike": ["bicycle", "cycle"],
        "couch": ["sofa", "sectional"],
        "desk": ["table", "workstation"],
        "chair": ["seat", "office chair"],
        "monitor": ["display", "screen"],
        "headphones": ["earbuds", "airpods", "headset"],
        "camera": ["dslr", "mirrorless"],
        "watch": ["smartwatch", "timepiece"],
        "tablet": ["ipad"],
        "console": ["playstation", "xbox", "nintendo"],
        "speaker": ["bluetooth speaker", "soundbar"],
        "keyboard": ["mechanical keyboard"],
        "mouse": ["trackpad", "wireless mouse"],
    }
    
    # Common brand names to extract
    BRANDS = [
        "apple", "samsung", "sony", "lg", "dell", "hp", "lenovo",
        "microsoft", "google", "amazon", "bose", "canon", "nikon",
        "nintendo", "playstation", "xbox", "ikea", "herman miller"
    ]
    
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
        Generate 3-5 query variations using Claude Haiku + local logic.
        
        Args:
            query: Original search query
            
        Returns:
            List of query variations (including original)
        """
        variations: Set[str] = {query.lower().strip(), query}
        
        # Try LLM-based generation first (Haiku is cheap: $0.25/MTok)
        if self.use_llm:
            llm_variations = self._generate_with_llm(query)
            variations.update(llm_variations)
        
        # Fallback to local logic if LLM unavailable or for additional coverage
        brand_variations = self._extract_brand_variations(query)
        variations.update(brand_variations)
        
        synonym_variations = self._get_synonym_variations(query)
        variations.update(synonym_variations)
        
        plural_variations = self._get_plural_singular(query)
        variations.update(plural_variations)
        
        spelling_variations = self._get_spelling_variations(query)
        variations.update(spelling_variations)
        
        # Return top 5 most relevant
        return list(variations)[:5]
    
    def _generate_with_llm(self, query: str) -> Set[str]:
        """
        Use Claude Haiku to generate intelligent query variations.
        Cost: ~$0.001 per query (very cheap)
        """
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model
                max_tokens=100,
                temperature=0.3,
                system="You are a search query optimizer for Facebook Marketplace. Generate 3-4 alternative search queries that would find the same items. Return ONLY the queries, one per line, no explanations.",
                messages=[{
                    "role": "user",
                    "content": f"Generate search variations for: {query}"
                }]
            )
            
            # Parse response
            text = response.content[0].text
            variations = set()
            for line in text.strip().split('\n'):
                clean = line.strip().strip('-').strip('*').strip()
                if clean and len(clean) > 2:
                    variations.add(clean.lower())
            
            return variations
        except Exception as e:
            # If LLM fails, return empty set (will use local fallbacks)
            print(f"LLM query generation failed: {e}")
            return set()
    
    def _extract_brand_variations(self, query: str) -> Set[str]:
        """Extract brand names and create variations"""
        variations = set()
        query_lower = query.lower()
        
        for brand in self.BRANDS:
            if brand in query_lower:
                # Version without brand
                without_brand = query_lower.replace(brand, "").strip()
                if without_brand:
                    variations.add(without_brand)
                
                # Version with just brand
                variations.add(brand)
        
        return variations
    
    def _get_synonym_variations(self, query: str) -> Set[str]:
        """Generate variations using synonym dictionary"""
        variations = set()
        query_lower = query.lower()
        
        for word, synonyms in self.SYNONYMS.items():
            if word in query_lower:
                for synonym in synonyms:
                    variations.add(query_lower.replace(word, synonym))
        
        return variations
    
    def _get_plural_singular(self, query: str) -> Set[str]:
        """Generate plural/singular variations"""
        variations = set()
        words = query.split()
        
        for i, word in enumerate(words):
            # Simple plural/singular rules
            if word.endswith('s') and len(word) > 3:
                # Try singular
                singular = word[:-1]
                new_query = ' '.join(words[:i] + [singular] + words[i+1:])
                variations.add(new_query)
            elif not word.endswith('s'):
                # Try plural
                plural = word + 's'
                new_query = ' '.join(words[:i] + [plural] + words[i+1:])
                variations.add(new_query)
        
        return variations
    
    def _get_spelling_variations(self, query: str) -> Set[str]:
        """Common spelling variations and abbreviations"""
        variations = set()
        query_lower = query.lower()
        
        # Common variations
        replacements = {
            "macbook pro": ["mac book pro", "mbp"],
            "iphone": ["i phone"],
            "playstation": ["play station", "ps"],
            "xbox": ["x box"],
            "nintendo switch": ["switch"],
        }
        
        for original, variants in replacements.items():
            if original in query_lower:
                for variant in variants:
                    variations.add(query_lower.replace(original, variant))
        
        return variations
    
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
