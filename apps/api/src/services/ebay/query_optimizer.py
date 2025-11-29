"""
eBay Query Optimizer - Extracts key product terms from verbose listing titles
for optimal eBay Browse API search results.
"""

import re
import os
from typing import List, Dict, Optional
import anthropic


class EbayQueryOptimizer:
    """
    Optimizes Facebook Marketplace listing titles for eBay search.
    
    Problem: FB titles like "Sony A7 IV Kit + G-Master Lenses + Godox Flash & Trigger 📸"
    are too specific and return no results on eBay.
    
    Solution: Extract the primary product (Sony A7 IV) and search for that,
    then optionally search for accessories separately.
    """
    
    # Common words to remove from queries
    STOP_WORDS = {
        'kit', 'bundle', 'set', 'lot', 'combo', 'package', 'deal',
        'with', 'and', 'plus', 'includes', 'included', 'comes',
        'great', 'excellent', 'good', 'perfect', 'mint', 'like new',
        'obo', 'firm', 'cash', 'only', 'pickup', 'local',
        'must', 'sell', 'need', 'gone', 'today', 'asap',
        'the', 'a', 'an', 'for', 'in', 'on', 'at', 'to'
    }
    
    # Known brand patterns
    BRANDS = {
        'camera': ['sony', 'canon', 'nikon', 'fuji', 'fujifilm', 'panasonic', 'olympus', 'leica', 'blackmagic', 'red'],
        'phone': ['apple', 'iphone', 'samsung', 'galaxy', 'google', 'pixel', 'oneplus'],
        'computer': ['apple', 'macbook', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'microsoft', 'surface'],
        'gaming': ['sony', 'playstation', 'ps5', 'ps4', 'microsoft', 'xbox', 'nintendo', 'switch'],
        'audio': ['sony', 'bose', 'apple', 'airpods', 'beats', 'sennheiser', 'audio-technica'],
    }
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
    
    def optimize_query(self, title: str, description: str = None) -> Dict[str, any]:
        """
        Optimize a listing title for eBay search.
        
        Args:
            title: Facebook Marketplace listing title
            description: Full listing description (optional but recommended)
            
        Returns:
            Dict with:
                - primary_query: Main product search term
                - secondary_queries: Additional items to search (accessories, etc.)
                - category_hint: Suggested eBay category
        """
        # Clean the title
        clean_title = self._clean_title(title)
        
        # Try LLM-based extraction first (most accurate)
        # Pass description for better context
        if self.client:
            result = self._extract_with_llm(title, description)
            if result and result.get('primary_query'):
                return result
        
        # Fallback to rule-based extraction
        return self._extract_with_rules(clean_title)
    
    def _clean_title(self, title: str) -> str:
        """Remove emojis, special chars, and normalize whitespace"""
        # Remove emojis
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        title = emoji_pattern.sub('', title)
        
        # Remove special characters but keep alphanumeric, spaces, and hyphens
        title = re.sub(r'[^\w\s\-]', ' ', title)
        
        # Normalize whitespace
        title = ' '.join(title.split())
        
        # Fix common model number formats (A7xii -> A7 II, A7riii -> A7R III)
        title = re.sub(r'([Aa]7)([xXrRsS]?)([iIvV]+)', lambda m: f"{m.group(1)}{m.group(2).upper()} {m.group(3).upper()}", title)
        
        return title.strip()
    
    def _extract_with_llm(self, title: str, description: str = None) -> Optional[Dict]:
        """Use Claude to extract the primary product from listing title AND description"""
        try:
            # Build the input - include description if available
            if description and len(description) > 20:
                user_input = f"TITLE: {title}\n\nDESCRIPTION: {description[:500]}"
            else:
                user_input = title
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0,
                system="""You are an expert at extracting product information from Facebook Marketplace listings for eBay price comparison.

Your task: Extract the PRIMARY product being sold. Use BOTH the title AND description to identify the exact product.

IMPORTANT: The title may be vague (like "Great deal!" or "Must sell!") but the description usually contains the actual product details. READ THE DESCRIPTION CAREFULLY.

RULES:
1. PRIMARY PRODUCT: Extract the main item being sold (brand + model + key specs)
   - Look in the description for brand names, model numbers, specifications
   - Fix common typos and abbreviations
   - Include important specs like storage size, color, generation
   - Keep it concise but specific enough to find the exact product on eBay
   
2. ACCESSORIES: Additional items included that have independent resale value
   - Only include items with brand names that can be searched separately
   - Skip generic items like "cables", "box", "manual", "charger"

3. CATEGORY: electronics, camera, phone, computer, gaming, audio, furniture, clothing, tools, sports, other

Return JSON format:
{"primary": "exact eBay search query", "accessories": ["item1", "item2"], "category": "category"}

EXAMPLES:
Title: "Great camera deal!" Description: "Selling my Sony A7 III with original box..." → {"primary": "Sony A7 III", "accessories": [], "category": "camera"}
Title: "Moving sale" Description: "iPhone 14 Pro 256GB Space Black, excellent condition" → {"primary": "iPhone 14 Pro 256GB", "accessories": [], "category": "phone"}
Title: "Sony A7xii (LENS NOT INCLUDED)" → {"primary": "Sony A7 II", "accessories": [], "category": "camera"}

Return ONLY valid JSON, nothing else.""",
                messages=[{"role": "user", "content": user_input}]
            )
            
            import json
            result_text = response.content[0].text.strip()
            
            # Parse JSON response
            try:
                parsed = json.loads(result_text)
                primary = parsed.get("primary", "")
                accessories = parsed.get("accessories", [])
                category = parsed.get("category", "other")
                
                if primary and 3 < len(primary) < 100:
                    return {
                        "primary_query": primary,
                        "secondary_queries": accessories[:3],  # Limit to 3
                        "category_hint": category,
                        "original_title": title
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, use the raw text as primary
                if result_text and 3 < len(result_text) < 100:
                    return {
                        "primary_query": result_text,
                        "secondary_queries": [],
                        "category_hint": self._detect_category(result_text),
                        "original_title": title
                    }
            
            return None
            
        except Exception as e:
            print(f"LLM query optimization failed: {e}")
            return None
    
    def _extract_with_rules(self, title: str) -> Dict:
        """Rule-based extraction as fallback"""
        words = title.lower().split()
        
        # Remove stop words
        filtered = [w for w in words if w not in self.STOP_WORDS]
        
        # Try to find brand + model pattern
        primary_parts = []
        
        for i, word in enumerate(filtered):
            # Check if it's a known brand
            is_brand = any(word in brands for brands in self.BRANDS.values())
            
            # Check if it looks like a model number (contains digits)
            has_digits = bool(re.search(r'\d', word))
            
            if is_brand or has_digits or len(primary_parts) < 3:
                primary_parts.append(word)
            
            # Stop after we have brand + model
            if len(primary_parts) >= 4:
                break
        
        primary_query = ' '.join(primary_parts[:4]) if primary_parts else title[:50]
        
        return {
            "primary_query": primary_query,
            "secondary_queries": [],
            "category_hint": self._detect_category(primary_query),
            "original_title": title
        }
    
    def _extract_accessories(self, title: str, primary: str) -> List[str]:
        """Extract accessory items from the title"""
        # Remove the primary product from title
        remaining = title.lower().replace(primary.lower(), '')
        
        # Common accessory patterns - more specific for better eBay search
        accessory_patterns = [
            r'(g-?master\s+lens(?:es)?)',  # Sony G-Master lenses
            r'(gm\s+lens(?:es)?)',
            r'(godox\s+\w+)',  # Godox flash/trigger
            r'(sigma\s+\d+(?:-\d+)?(?:mm)?)',  # Sigma lenses
            r'(tamron\s+\d+(?:-\d+)?(?:mm)?)',  # Tamron lenses
            r'(\d+(?:-\d+)?mm\s+(?:f/?[\d.]+\s+)?lens)',  # Generic lens with focal length
            r'(\w+\s+flash)',
            r'(\w+\s+trigger)',
            r'(\w+\s+controller(?:s)?)',
            r'(\w+\s+battery\s+grip)',
            r'(magic\s+mouse)',
            r'(magic\s+keyboard)',
            r'(airpods?\s*(?:pro)?)',
        ]
        
        accessories = []
        for pattern in accessory_patterns:
            matches = re.findall(pattern, remaining, re.IGNORECASE)
            for match in matches:
                clean = match.strip()
                if clean and len(clean) > 3 and clean not in accessories:
                    accessories.append(clean)
        
        return accessories[:3]  # Limit to 3 accessories
    
    def _detect_category(self, query: str) -> str:
        """Detect the likely eBay category"""
        query_lower = query.lower()
        
        # Camera keywords
        if any(kw in query_lower for kw in ['sony a7', 'canon eos', 'nikon', 'fuji', 'camera', 'lens']):
            return "Cameras & Photo"
        
        # Phone keywords
        if any(kw in query_lower for kw in ['iphone', 'samsung', 'galaxy', 'pixel', 'phone']):
            return "Cell Phones & Accessories"
        
        # Computer keywords
        if any(kw in query_lower for kw in ['macbook', 'laptop', 'dell', 'hp', 'lenovo', 'computer']):
            return "Computers/Tablets & Networking"
        
        # Gaming keywords
        if any(kw in query_lower for kw in ['ps5', 'playstation', 'xbox', 'nintendo', 'switch', 'gaming']):
            return "Video Games & Consoles"
        
        return "All Categories"


def optimize_for_ebay(title: str) -> str:
    """
    Convenience function to get optimized eBay search query.
    
    Args:
        title: Facebook Marketplace listing title
        
    Returns:
        Optimized search query for eBay
    """
    optimizer = EbayQueryOptimizer()
    result = optimizer.optimize_query(title)
    return result["primary_query"]
