"""
Search routes for Facebook Marketplace.
"""

import logging
import time
from fastapi import APIRouter, HTTPException
from typing import List

from src.models import SearchQuery, SearchResult, Listing
from src.services.search import SearchOrchestrator
from src.services.browser import MarketplaceScraper
from src.db import get_pg_pool

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResult)
async def search_marketplace(query: SearchQuery):
    """
    Search Facebook Marketplace with query variations.
    
    1. Generates query variations using LLM
    2. Checks Redis cache
    3. If not cached, scrapes each URL
    4. Deduplicates results
    5. Caches for 5 minutes
    6. Returns results with metadata
    """
    start_time = time.time()
    orchestrator = SearchOrchestrator()
    
    try:
        # Check cache first
        cached_result = await orchestrator.check_cache(query)
        if cached_result:
            cached_result.cached = True
            cached_result.search_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Cache hit for query: {query.query}")
            return cached_result
        
        # Prepare search (generate variations and URLs)
        search_prep = await orchestrator.prepare_search(query)
        logger.info(f"Generated {len(search_prep['query_variations'])} variations")
        
        # Scrape each URL
        scraper = MarketplaceScraper()
        all_listings: List[Listing] = []
        
        for url in search_prep['urls_to_scrape']:
            try:
                listings = await scraper.search_listings(url)
                all_listings.extend(listings)
                logger.info(f"Scraped {len(listings)} listings from {url}")
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                continue
        
        # Deduplicate
        unique_listings = orchestrator.deduplicate_listings(all_listings)
        logger.info(f"Deduplicated to {len(unique_listings)} unique listings")
        
        # Save to database
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            for listing in unique_listings:
                try:
                    await conn.execute("""
                        INSERT INTO listings (
                            id, title, price, price_value, location,
                            image_url, url, seller_name, scraped_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (id) DO UPDATE
                        SET scraped_at = EXCLUDED.scraped_at
                    """,
                        listing.id, listing.title, listing.price,
                        listing.price_value, listing.location,
                        listing.image_url, listing.url,
                        listing.seller_name, listing.scraped_at
                    )
                except Exception as e:
                    logger.error(f"Failed to save listing {listing.id}: {e}")
            
            # Save search history
            await conn.execute("""
                INSERT INTO search_history (
                    query, min_price, max_price, location, results_count
                )
                VALUES ($1, $2, $3, $4, $5)
            """,
                query.query, query.min_price, query.max_price,
                query.location, len(unique_listings)
            )
        
        # Create result
        result = SearchResult(
            listings=unique_listings,
            total_count=len(unique_listings),
            query_variations=search_prep['query_variations'],
            cached=False,
            search_time_ms=(time.time() - start_time) * 1000
        )
        
        # Cache result
        await orchestrator.cache_results(query, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/suggestions")
async def get_suggestions(q: str):
    """
    Get query suggestions for autocomplete.
    
    Args:
        q: Partial query string
        
    Returns:
        List of suggested queries
    """
    from src.services.search import QueryGenerator
    
    try:
        generator = QueryGenerator()
        variations = generator.generate_variations(q)
        return {"suggestions": variations}
    except Exception as e:
        logger.error(f"Suggestion generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
