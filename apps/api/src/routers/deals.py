"""
Deal routes for scored listings.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from src.models import Deal, Listing, DealRating
from src.services.reseller import DealScorer, HotDealDetector
from src.db import get_pg_pool

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/deals", response_model=List[Deal])
async def list_deals(
    rating: Optional[str] = Query(None, description="Filter by rating: HOT, GOOD, FAIR, PASS"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return")
):
    """
    List deals with optional rating filter.
    
    Fetches recent listings from database, scores them using LLM,
    and returns only deals matching the rating filter.
    """
    try:
        # Fetch recent listings from database
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM listings
                ORDER BY scraped_at DESC
                LIMIT $1
            """, limit * 2)  # Fetch more since we'll filter
        
        # Convert to Listing objects
        listings = [
            Listing(
                id=row['id'],
                title=row['title'],
                price=row['price'],
                price_value=row['price_value'],
                location=row['location'],
                image_url=row['image_url'],
                url=row['url'],
                seller_name=row['seller_name'],
                scraped_at=row['scraped_at'],
                created_at=row['created_at']
            )
            for row in rows
        ]
        
        # Score all listings
        scorer = DealScorer()
        deals = []
        
        for listing in listings:
            try:
                deal = scorer.score_listing(listing)
                
                # Apply rating filter
                if rating:
                    if deal.deal_rating.value == rating.upper():
                        deals.append(deal)
                else:
                    deals.append(deal)
                    
            except Exception as e:
                logger.error(f"Failed to score listing {listing.id}: {e}")
                continue
        
        # Sort by rating and profit
        deals.sort(
            key=lambda d: (
                0 if d.deal_rating == DealRating.HOT else
                1 if d.deal_rating == DealRating.GOOD else
                2 if d.deal_rating == DealRating.FAIR else 3,
                -(d.profit_estimate or 0)
            )
        )
        
        return deals[:limit]
        
    except Exception as e:
        logger.error(f"Failed to list deals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deals/{listing_id}", response_model=Deal)
async def get_deal(listing_id: str):
    """
    Get a single deal by listing ID.
    
    Fetches listing from database and scores it.
    """
    try:
        # Fetch listing
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM listings WHERE id = $1
            """, listing_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Convert to Listing
        listing = Listing(
            id=row['id'],
            title=row['title'],
            price=row['price'],
            price_value=row['price_value'],
            location=row['location'],
            image_url=row['image_url'],
            url=row['url'],
            seller_name=row['seller_name'],
            scraped_at=row['scraped_at'],
            created_at=row['created_at']
        )
        
        # Score it
        scorer = DealScorer()
        deal = scorer.score_listing(listing)
        
        return deal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deal {listing_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deals/{listing_id}/track")
async def track_deal(listing_id: str):
    """
    Track a deal for price monitoring.
    
    (Placeholder for future implementation)
    """
    return {
        "message": "Deal tracking not yet implemented",
        "listing_id": listing_id
    }


@router.get("/deals/hot/trending")
async def get_hot_deals():
    """
    Get currently hot deals (HOT and GOOD ratings only).
    Fetches pre-scored deals from the database.
    """
    try:
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            # Fetch deals that are already scored as HOT or GOOD
            rows = await conn.fetch("""
                SELECT l.*, d.ebay_avg_price, d.profit_estimate, d.roi_percent,
                       d.deal_rating, d.why_standout, d.category, d.match_score
                FROM listings l
                JOIN deals d ON l.id = d.listing_id
                WHERE d.deal_rating IN ('HOT', 'GOOD')
                ORDER BY 
                    CASE d.deal_rating 
                        WHEN 'HOT' THEN 0 
                        WHEN 'GOOD' THEN 1 
                        ELSE 2 
                    END,
                    d.profit_estimate DESC NULLS LAST,
                    l.scraped_at DESC
                LIMIT 20
            """)
        
        # Convert to Deal objects
        deals = []
        for row in rows:
            deal = Deal(
                id=row['id'],
                title=row['title'],
                price=row['price'],
                price_value=row['price_value'],
                location=row['location'],
                image_url=row['image_url'],
                url=row['url'],
                seller_name=row['seller_name'],
                description=row.get('description'),
                scraped_at=row['scraped_at'],
                created_at=row['created_at'],
                ebay_avg_price=row['ebay_avg_price'],
                profit_estimate=row['profit_estimate'],
                roi_percent=row['roi_percent'],
                deal_rating=DealRating(row['deal_rating']),
                is_new=True,
                price_changed=False,
                old_price=None,
                why_standout=row['why_standout'],
                category=row['category'],
                match_score=row['match_score']
            )
            deals.append(deal)
        
        # Get trending categories
        detector = HotDealDetector()
        
        return {
            "deals": deals,
            "total_count": len(deals),
            "trending_categories": detector.get_trending_categories()
        }
        
    except Exception as e:
        logger.error(f"Failed to get hot deals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deals/view")
async def view_deal(url: str = Query(..., description="Facebook Marketplace listing URL")):
    """
    View and analyze a specific deal from a URL.
    
    This endpoint:
    1. Checks Redis cache for previous analysis (1 hour TTL)
    2. If not cached, scrapes the listing details from Facebook Marketplace
    3. Analyzes it with eBay price data
    4. Caches the result for 1 hour
    5. Returns actionable next steps
    
    Example: POST /api/deals/view?url=https://facebook.com/marketplace/item/123456
    """
    import json
    import hashlib
    from src.db import get_redis
    
    try:
        from src.services.enhanced_deal_viewer import EnhancedDealViewer
        from src.services.browser import MarketplaceScraper
        
        logger.info(f"Viewing deal: {url}")
        
        # Check Redis cache first
        cache_key = f"deal_view:{hashlib.md5(url.encode()).hexdigest()}"
        try:
            redis_client = get_redis()
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache hit for deal: {url}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")
        
        # Scrape the listing
        scraper = MarketplaceScraper()
        listing_data = await scraper.scrape_single_listing(url)
        
        if not listing_data:
            raise HTTPException(status_code=404, detail="Could not scrape listing from URL")
        
        # Analyze with eBay integration
        viewer = EnhancedDealViewer()
        result = await viewer.view_and_analyze_deal(
            listing_data=listing_data,
            use_ai=True,
            min_rating=DealRating.FAIR
        )
        
        logger.info(f"Deal analysis complete: {result['analysis']['rating']}")
        
        # Cache the result for 1 hour
        try:
            # Convert DealRating enum to string for JSON serialization
            cache_result = result.copy()
            if 'analysis' in cache_result and 'rating' in cache_result['analysis']:
                if hasattr(cache_result['analysis']['rating'], 'value'):
                    cache_result['analysis']['rating'] = cache_result['analysis']['rating'].value
            await redis_client.setex(cache_key, 3600, json.dumps(cache_result))
            logger.info(f"Cached deal analysis for 1 hour: {url}")
        except Exception as e:
            logger.warning(f"Failed to cache deal analysis: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to view deal: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze deal: {str(e)}")
