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
        
        # Pre-filter: only score listings with valid prices
        scorable_listings = [
            l for l in unique_listings 
            if l.price_value and l.price_value > 0
        ]
        
        # Limit to top 15 listings to keep it fast (each takes ~1-2 seconds)
        max_to_score = 15
        if len(scorable_listings) > max_to_score:
            logger.info(f"Limiting scoring to {max_to_score} out of {len(scorable_listings)} listings")
            scorable_listings = scorable_listings[:max_to_score]
        
        # Score listings in parallel
        from src.services.reseller import DealScorer, HotDealDetector
        import asyncio
        
        scorer = DealScorer()
        hot_deal_detector = HotDealDetector()
        
        # Score in batches of 5 to avoid rate limits
        batch_size = 5
        deals = []
        
        for i in range(0, len(scorable_listings), batch_size):
            batch = scorable_listings[i:i+batch_size]
            batch_deals = await asyncio.gather(
                *[asyncio.to_thread(scorer.score_listing, listing) for listing in batch],
                return_exceptions=True
            )
            
            for deal in batch_deals:
                if isinstance(deal, Exception):
                    logger.error(f"Failed to score listing: {deal}")
                else:
                    deals.append(deal)
        
        logger.info(f"Scored {len(deals)} listings")
        
        # Filter to only hot/good deals
        hot_deals = hot_deal_detector.filter_hot_deals(deals)
        logger.info(f"Found {len(hot_deals)} hot/good deals out of {len(deals)} scored listings")
        
        # Save to database
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            # Save all listings
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
            
            # Save scored deals
            for deal in hot_deals:
                try:
                    await conn.execute("""
                        INSERT INTO deals (
                            listing_id, ebay_avg_price, profit_estimate, roi_percent,
                            deal_rating, why_standout, category, match_score
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (listing_id) DO UPDATE
                        SET ebay_avg_price = EXCLUDED.ebay_avg_price,
                            profit_estimate = EXCLUDED.profit_estimate,
                            roi_percent = EXCLUDED.roi_percent,
                            deal_rating = EXCLUDED.deal_rating,
                            why_standout = EXCLUDED.why_standout,
                            category = EXCLUDED.category,
                            match_score = EXCLUDED.match_score
                    """,
                        deal.id, deal.ebay_avg_price, deal.profit_estimate,
                        deal.roi_percent, deal.deal_rating.value,
                        deal.why_standout, deal.category, deal.match_score
                    )
                except Exception as e:
                    logger.error(f"Failed to save deal {deal.id}: {e}")
            
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
        
        # Create result with scored deals
        result = SearchResult(
            listings=hot_deals,  # Return only hot/good deals
            total_count=len(hot_deals),
            query_variations=search_prep['query_variations'],
            cached=False,
            search_time_ms=(time.time() - start_time) * 1000
        )
        
        # Cache result
        await orchestrator.cache_results(query, result)
        
        logger.info(f"Returning {len(hot_deals)} deals to frontend")
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
