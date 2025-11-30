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
        
        # Score listings using eBay price comparison
        from src.services.ebay import DealAnalyzer
        from src.services.reseller import HotDealDetector
        from src.models import Deal, DealRating
        
        # Check database for existing analyzed deals (avoid re-analyzing)
        pool = get_pg_pool()
        listing_ids = [l.id for l in unique_listings]
        existing_deals = {}
        
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT l.*, d.ebay_avg_price, d.profit_estimate, d.roi_percent,
                       d.deal_rating, d.why_standout, d.category, d.match_score
                FROM listings l
                JOIN deals d ON l.id = d.listing_id
                WHERE l.id = ANY($1)
            """, listing_ids)
            
            for row in rows:
                existing_deals[row['id']] = Deal(
                    id=row['id'],
                    title=row['title'],
                    price=row['price'],
                    price_value=row['price_value'],
                    location=row['location'],
                    image_url=row['image_url'],
                    url=row['url'],
                    seller_name=row['seller_name'],
                    scraped_at=row['scraped_at'],
                    created_at=row['created_at'],
                    ebay_avg_price=row['ebay_avg_price'],
                    profit_estimate=row['profit_estimate'],
                    roi_percent=row['roi_percent'],
                    deal_rating=DealRating(row['deal_rating']),
                    is_new=False,
                    price_changed=False,
                    old_price=None,
                    why_standout=row['why_standout'],
                    category=row['category'],
                    match_score=row['match_score']
                )
        
        logger.info(f"Found {len(existing_deals)} existing analyzed deals in database")
        
        # Filter to listings that need analysis
        listings_to_analyze = [
            l for l in unique_listings 
            if l.id not in existing_deals and l.price_value and l.price_value > 0
        ]
        
        # Limit new analyses to keep it fast
        max_to_score = 10
        if len(listings_to_analyze) > max_to_score:
            logger.info(f"Limiting new analyses to {max_to_score} out of {len(listings_to_analyze)} listings")
            listings_to_analyze = listings_to_analyze[:max_to_score]
        analyzer = DealAnalyzer()
        hot_deal_detector = HotDealDetector()
        
        # Start with existing deals from database
        deals = list(existing_deals.values())
        logger.info(f"Starting with {len(deals)} cached deals from database")
        
        async def analyze_listing(listing):
            """Analyze a single listing with eBay data"""
            try:
                analysis = await analyzer.analyze_deal(
                    listing_title=listing.title,
                    listing_price=listing.price_value,
                    listing_condition="USED",
                    listing_description=None,
                    use_ai=True
                )
                
                # Convert to Deal object
                listing_data = listing.model_dump()
                listing_data.update({
                    'ebay_avg_price': analysis.get('ebay_avg_price'),
                    'profit_estimate': analysis.get('profit_estimate'),
                    'roi_percent': analysis.get('roi_percent'),
                    'deal_rating': analysis.get('deal_rating', DealRating.FAIR),
                    'is_new': True,
                    'price_changed': False,
                    'old_price': None,
                    'why_standout': analysis.get('reason', ''),
                    'category': analysis.get('category_hint', ''),
                    'match_score': analysis.get('score', 50) / 100.0
                })
                return Deal(**listing_data)
            except Exception as e:
                logger.error(f"Failed to analyze listing {listing.id}: {e}")
                return None
        
        # Only analyze NEW listings (not in database)
        new_deals = []
        for listing in listings_to_analyze:
            try:
                deal = await analyze_listing(listing)
                if deal:
                    new_deals.append(deal)
                    deals.append(deal)
            except Exception as e:
                logger.error(f"Failed to score listing: {e}")
        
        logger.info(f"Analyzed {len(new_deals)} new listings (total: {len(deals)})")
        
        # Filter to only hot/good deals
        hot_deals = hot_deal_detector.filter_hot_deals(deals)
        logger.info(f"Found {len(hot_deals)} hot/good deals out of {len(deals)} scored listings")
        
        # Save NEW data to database (skip existing)
        if new_deals:
            async with pool.acquire() as conn:
                # Save new listings
                for listing in listings_to_analyze:
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
                
                # Save new deals only
                for deal in new_deals:
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
