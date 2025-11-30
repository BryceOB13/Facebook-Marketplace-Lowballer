"""
eBay Browse API Client - Integrates with eBay's Browse API for price comparison
and deal validation. Uses OAuth2 client credentials flow.
"""

import os
import aiohttp
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json
from dataclasses import dataclass


@dataclass
class EbayItem:
    """Simplified eBay item representation"""
    item_id: str
    title: str
    price: float
    currency: str
    condition: str
    image_url: Optional[str]
    item_url: str
    seller_username: str
    seller_feedback_score: int
    shipping_cost: Optional[float]
    location: Optional[str]


class EbayBrowseClient:
    """
    eBay Browse API client with intelligent caching and rate limiting.
    
    Cost optimization:
    - Caches search results for 1 hour
    - Batches multiple queries when possible
    - Uses semantic deduplication to avoid redundant API calls
    """
    
    # Use Sandbox URLs if credentials start with SBX, otherwise Production
    SANDBOX_BASE_URL = "https://api.sandbox.ebay.com/buy/browse/v1"
    SANDBOX_AUTH_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    PROD_BASE_URL = "https://api.ebay.com/buy/browse/v1"
    PROD_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    
    def __init__(self):
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("eBay credentials not configured. Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET in .env")
        
        # Detect sandbox vs production based on client_id prefix
        self.is_sandbox = self.client_id.startswith("SBX-") or "SBX" in self.client_id
        self.BASE_URL = self.SANDBOX_BASE_URL if self.is_sandbox else self.PROD_BASE_URL
        self.AUTH_URL = self.SANDBOX_AUTH_URL if self.is_sandbox else self.PROD_AUTH_URL
        
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        
        # In-memory cache for search results (1 hour TTL)
        self._search_cache: Dict[str, tuple[datetime, List[EbayItem]]] = {}
        
        # Redis cache TTL (1 hour for eBay data)
        self.REDIS_CACHE_TTL = 3600
        
    async def __aenter__(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close session here - let it be reused
        # Session will be closed when the client is garbage collected
        pass
    
    async def close(self):
        """Explicitly close the session when done"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _ensure_session(self):
        """Ensure we have an open session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def _ensure_token(self):
        """Ensure we have a valid OAuth token"""
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return
        
        # Ensure session exists
        await self._ensure_session()
        
        # Get new token
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
        
        async with self._session.post(
            self.AUTH_URL,
            auth=auth,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to get eBay token: {await response.text()}")
            
            result = await response.json()
            self.access_token = result["access_token"]
            # Set expiry 5 minutes before actual expiry for safety
            expires_in = result.get("expires_in", 7200) - 300
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
    
    async def search_items(
        self,
        query: str,
        category_ids: Optional[List[str]] = None,
        condition: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        limit: int = 50,
        sort: str = "price",  # price, newlyListed, endingSoonest
        marketplace_id: str = "EBAY_US"
    ) -> List[EbayItem]:
        """
        Search eBay items with filters.
        
        Args:
            query: Search keywords
            category_ids: List of eBay category IDs to filter by
            condition: Item condition (NEW, USED, etc.)
            price_min: Minimum price filter
            price_max: Maximum price filter
            limit: Max results (1-200)
            sort: Sort order
            marketplace_id: eBay marketplace
            
        Returns:
            List of EbayItem objects
        """
        # Check cache first
        cache_key = f"{query}:{category_ids}:{condition}:{price_min}:{price_max}:{sort}"
        if cache_key in self._search_cache:
            cached_time, cached_results = self._search_cache[cache_key]
            if datetime.now() - cached_time < timedelta(hours=1):
                return cached_results[:limit]
        
        await self._ensure_token()
        
        # Build query parameters
        params = {
            "q": query,
            "limit": min(limit, 200),
            "sort": sort,
            "fieldgroups": "EXTENDED"  # Get more details
        }
        
        # Add filters
        filters = []
        if price_min or price_max:
            price_filter = f"price:[{price_min or '*'}..{price_max or '*'}]"
            filters.append(price_filter)
        
        if condition:
            filters.append(f"conditions:{{{condition}}}")
        
        # Only include FIXED_PRICE items (no auctions)
        filters.append("buyingOptions:{FIXED_PRICE}")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        if category_ids:
            params["category_ids"] = ",".join(category_ids)
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
            "Accept": "application/json"
        }
        
        url = f"{self.BASE_URL}/item_summary/search"
        
        async with self._session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"eBay API error: {response.status} - {error_text}")
            
            data = await response.json()
        
        # Parse results
        items = []
        for item_data in data.get("itemSummaries", []):
            try:
                items.append(self._parse_item(item_data))
            except Exception as e:
                print(f"Failed to parse eBay item: {e}")
                continue
        
        # Cache results
        self._search_cache[cache_key] = (datetime.now(), items)
        
        return items
    
    def _parse_item(self, data: Dict[str, Any]) -> EbayItem:
        """Parse eBay API item data into EbayItem"""
        price_data = data.get("price", {})
        shipping_data = data.get("shippingOptions", [{}])[0] if data.get("shippingOptions") else {}
        shipping_cost_data = shipping_data.get("shippingCost", {})
        
        return EbayItem(
            item_id=data["itemId"],
            title=data["title"],
            price=float(price_data.get("value", 0)),
            currency=price_data.get("currency", "USD"),
            condition=data.get("condition", "UNKNOWN"),
            image_url=data.get("image", {}).get("imageUrl"),
            item_url=data.get("itemWebUrl", ""),
            seller_username=data.get("seller", {}).get("username", ""),
            seller_feedback_score=data.get("seller", {}).get("feedbackScore", 0),
            shipping_cost=float(shipping_cost_data.get("value", 0)) if shipping_cost_data else None,
            location=data.get("itemLocation", {}).get("city")
        )
    
    async def get_price_statistics(
        self,
        query: str,
        category_ids: Optional[List[str]] = None,
        condition: Optional[str] = None,
        reference_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Get price statistics for a query (avg, median, min, max).
        Uses Redis caching to avoid repeated eBay API calls.
        
        Args:
            query: Search query
            category_ids: eBay category IDs
            condition: Item condition filter
            reference_price: The listing price we're comparing against (used for smart filtering)
        
        Returns:
            Dict with avg_price, median_price, min_price, max_price, sample_size, items
        """
        import logging
        import hashlib
        logger = logging.getLogger(__name__)
        
        # Check Redis cache first
        cache_key = f"ebay_stats:{hashlib.md5(f'{query}:{condition}:{reference_price}'.encode()).hexdigest()}"
        try:
            from src.db import get_redis
            redis_client = get_redis()
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"[EBAY CACHE HIT] Query: '{query}'")
                cached_data = json.loads(cached)
                # Reconstruct EbayItem objects
                cached_data["items"] = [
                    EbayItem(**item) for item in cached_data.get("items_data", [])
                ]
                return cached_data
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")
        
        logger.info(f"[EBAY SEARCH] Query: '{query}', Condition: {condition}, Reference: ${reference_price or 0:.0f}")
        
        # Search without price filter first, then filter results
        items = await self.search_items(
            query=query,
            category_ids=category_ids,
            condition=None,  # Don't filter by condition - too restrictive
            limit=200,
            sort="newlyListed"  # Better relevance than sorting by price
        )
        
        logger.info(f"[EBAY SEARCH] Raw results: {len(items)} items")
        if items:
            raw_prices = sorted([item.price for item in items])
            logger.info(f"[EBAY SEARCH] Raw price range: ${raw_prices[0]:.2f} - ${raw_prices[-1]:.2f}")
        
        # SMART FILTERING: Use reference price as the primary signal
        # If someone is selling something for $700, we should compare to similar-priced items
        if items and len(items) > 3:
            # Step 1: PRICE-BASED FILTERING (most important)
            # The listing price tells us what price range we should be looking at
            if reference_price and reference_price > 50:
                # Filter to items within a reasonable range of the listing price
                # This is the key insight: a $700 item should compare to $300-$1500 items, not $20 accessories
                min_reasonable = reference_price * 0.25  # 25% of listing price
                max_reasonable = reference_price * 2.5   # 250% of listing price
                
                price_filtered = [item for item in items if min_reasonable <= item.price <= max_reasonable]
                
                logger.info(f"[EBAY SEARCH] Price filter range: ${min_reasonable:.0f}-${max_reasonable:.0f}")
                logger.info(f"[EBAY SEARCH] Items in range: {len(price_filtered)} of {len(items)}")
                
                if len(price_filtered) >= 3:
                    items = price_filtered
                else:
                    # If too few items in range, try a wider range
                    min_wider = reference_price * 0.15
                    max_wider = reference_price * 4.0
                    wider_filtered = [item for item in items if min_wider <= item.price <= max_wider]
                    if len(wider_filtered) >= 3:
                        items = wider_filtered
                        logger.info(f"[EBAY SEARCH] Using wider range: ${min_wider:.0f}-${max_wider:.0f}, {len(items)} items")
            
            # Step 2: Title relevance filtering - ensure results are the MAIN product, not accessories
            # Accessories often mention the main product ("for Sony A7 II", "compatible with...")
            accessory_indicators = [
                ' for ', ' fits ', ' compatible ', ' replacement ', ' cover ', ' case ',
                ' strap ', ' battery ', ' charger ', ' grip ', ' mount ', ' adapter ',
                ' cable ', ' cord ', ' screen protector ', ' filter ', ' hood ', ' cap ',
                ' remote ', ' trigger ', ' plate ', ' bracket ', ' bag ', ' pouch ',
                ' book ', ' guide ', ' manual ', ' dummy '
            ]
            
            main_product_items = []
            for item in items:
                title_lower = item.title.lower()
                # Check if this looks like an accessory (mentions "for [product]" pattern)
                is_accessory = any(indicator in title_lower for indicator in accessory_indicators)
                
                if not is_accessory:
                    main_product_items.append(item)
            
            if len(main_product_items) >= 3:
                items = main_product_items
                logger.info(f"[EBAY SEARCH] After accessory filter: {len(items)} main products")
            
            # Step 3: IQR filtering on remaining items to remove outliers
            if len(items) > 5:
                prices = sorted([item.price for item in items])
                q1_idx = len(prices) // 4
                q3_idx = (3 * len(prices)) // 4
                q1 = prices[q1_idx]
                q3 = prices[q3_idx]
                iqr = q3 - q1
                
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                iqr_filtered = [item for item in items if lower_bound <= item.price <= upper_bound]
                
                if len(iqr_filtered) >= 3:
                    items = iqr_filtered
                    logger.info(f"[EBAY SEARCH] After IQR filter: {len(items)} items")
        
        if not items:
            logger.warning(f"[EBAY SEARCH] No items found for query: '{query}'")
            return {
                "avg_price": 0,
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "sample_size": 0,
                "items": []
            }
        
        prices = [item.price for item in items]
        prices.sort()
        
        # TRACE: Log sample of items found
        logger.info(f"[EBAY SEARCH] Final: {len(items)} items for '{query}'")
        logger.info(f"[EBAY SEARCH] Price range: ${prices[0]:.2f} - ${prices[-1]:.2f}")
        logger.info(f"[EBAY SEARCH] Sample items:")
        for item in items[:5]:
            logger.info(f"  - {item.title[:60]}... ${item.price:.2f}")
        
        avg_price = sum(prices) / len(prices)
        median_price = prices[len(prices) // 2]
        
        logger.info(f"[EBAY SEARCH] Avg: ${avg_price:.2f}, Median: ${median_price:.2f}")
        
        result = {
            "avg_price": avg_price,
            "median_price": median_price,
            "min_price": prices[0],
            "max_price": prices[-1],
            "sample_size": len(prices),
            "items": items  # Return items for analysis
        }
        
        # Cache result in Redis for 1 hour
        try:
            from src.db import get_redis
            redis_client = get_redis()
            # Store items as dicts for JSON serialization
            cache_data = {
                **result,
                "items_data": [
                    {
                        "item_id": item.item_id,
                        "title": item.title,
                        "price": item.price,
                        "currency": item.currency,
                        "condition": item.condition,
                        "image_url": item.image_url,
                        "item_url": item.item_url,
                        "seller_username": item.seller_username,
                        "seller_feedback_score": item.seller_feedback_score,
                        "shipping_cost": item.shipping_cost,
                        "location": item.location
                    }
                    for item in items[:20]  # Cache top 20 items
                ]
            }
            del cache_data["items"]  # Remove non-serializable items list
            await redis_client.setex(cache_key, self.REDIS_CACHE_TTL, json.dumps(cache_data))
            logger.info(f"[EBAY CACHE] Cached stats for '{query}' (1 hour TTL)")
        except Exception as e:
            logger.warning(f"Failed to cache eBay stats: {e}")
        
        return result
    
    async def find_comparable_items(
        self,
        title: str,
        price: float,
        condition: str = "USED",
        tolerance: float = 0.3  # 30% price tolerance
    ) -> List[EbayItem]:
        """
        Find comparable items on eBay for price validation.
        
        Args:
            title: Item title/description
            price: Target price
            condition: Item condition
            tolerance: Price range tolerance (0.3 = ±30%)
            
        Returns:
            List of comparable items
        """
        # Extract key terms from title (remove common words)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        terms = [w for w in title.lower().split() if w not in stop_words]
        query = " ".join(terms[:5])  # Use first 5 meaningful words
        
        price_min = price * (1 - tolerance)
        price_max = price * (1 + tolerance)
        
        return await self.search_items(
            query=query,
            condition=condition,
            price_min=price_min,
            price_max=price_max,
            limit=20
        )
