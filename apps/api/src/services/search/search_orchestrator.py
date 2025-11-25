"""
Search orchestrator - coordinates query generation, URL building, and result deduplication.
"""

import hashlib
import json
from typing import List, Set
from datetime import timedelta

from src.models import SearchQuery, SearchResult, Listing
from src.db import get_redis
from .query_generator import QueryGenerator
from .url_builder import MarketplaceURLBuilder


class SearchOrchestrator:
    """Orchestrate the complete search workflow"""
    
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self):
        self.query_generator = QueryGenerator()
        self.url_builder = MarketplaceURLBuilder()
    
    async def prepare_search(self, search_query: SearchQuery) -> dict:
        """
        Prepare search by generating variations and URLs.
        Does NOT perform actual scraping - just preparation.
        
        Args:
            search_query: Search parameters
            
        Returns:
            Dict with query_variations and urls_to_scrape
        """
        # Generate query variations
        variations = self.query_generator.generate_variations(search_query.query)
        
        # Build URLs for each variation
        urls = []
        for variation in variations:
            url = self.url_builder.build_search_url(
                query=variation,
                min_price=search_query.min_price,
                max_price=search_query.max_price,
                location=search_query.location
            )
            urls.append(url)
        
        # Get category keywords
        categories = self.query_generator.get_category_keywords(search_query.query)
        
        return {
            "query_variations": variations,
            "urls_to_scrape": urls,
            "categories": categories
        }
    
    async def check_cache(self, search_query: SearchQuery) -> SearchResult | None:
        """
        Check if search results are cached.
        
        Args:
            search_query: Search parameters
            
        Returns:
            Cached SearchResult or None
        """
        try:
            redis = get_redis()
            cache_key = self._get_cache_key(search_query)
            
            cached_data = await redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return SearchResult(**data)
            
            return None
        except Exception:
            # If cache fails, just return None
            return None
    
    async def cache_results(self, search_query: SearchQuery, result: SearchResult):
        """
        Cache search results.
        
        Args:
            search_query: Search parameters
            result: Search results to cache
        """
        try:
            redis = get_redis()
            cache_key = self._get_cache_key(search_query)
            
            # Convert to dict for JSON serialization
            data = result.model_dump()
            await redis.setex(
                cache_key,
                self.CACHE_TTL,
                json.dumps(data, default=str)
            )
        except Exception:
            # If caching fails, just continue
            pass
    
    def deduplicate_listings(self, listings: List[Listing]) -> List[Listing]:
        """
        Remove duplicate listings by ID.
        
        Args:
            listings: List of listings (may contain duplicates)
            
        Returns:
            Deduplicated list
        """
        seen_ids: Set[str] = set()
        unique_listings = []
        
        for listing in listings:
            if listing.id not in seen_ids:
                seen_ids.add(listing.id)
                unique_listings.append(listing)
        
        return unique_listings
    
    def _get_cache_key(self, search_query: SearchQuery) -> str:
        """Generate cache key from search query"""
        # Create a stable hash of the query parameters
        query_str = f"{search_query.query}:{search_query.min_price}:{search_query.max_price}:{search_query.location}"
        hash_obj = hashlib.md5(query_str.encode())
        return f"search:{hash_obj.hexdigest()}"
