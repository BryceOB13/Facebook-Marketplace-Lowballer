"""
Database connection and initialization.
"""

import asyncpg
import redis.asyncio as redis
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global connection pools
pg_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None


async def init_db():
    """Initialize database connections"""
    global pg_pool, redis_client
    
    # PostgreSQL
    database_url = os.getenv("DATABASE_URL", "postgresql://dealscout:localdev@localhost:5432/dealscout")
    try:
        pg_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
        logger.info("PostgreSQL connection pool created")
        
        # Create tables
        await create_tables()
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise
    
    # Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_db():
    """Close database connections"""
    global pg_pool, redis_client
    
    if pg_pool:
        await pg_pool.close()
        logger.info("PostgreSQL connection pool closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def create_tables():
    """Create database tables if they don't exist"""
    async with pg_pool.acquire() as conn:
        # Listings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                price TEXT,
                price_value INTEGER,
                location TEXT,
                image_url TEXT,
                url TEXT NOT NULL,
                seller_name TEXT,
                scraped_at TIMESTAMP NOT NULL DEFAULT NOW(),
                match_score FLOAT,
                match_reason TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_price_value ON listings(price_value);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_scraped_at ON listings(scraped_at);
        """)
        
        # Negotiations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS negotiations (
                id SERIAL PRIMARY KEY,
                listing_id TEXT NOT NULL REFERENCES listings(id),
                state TEXT NOT NULL,
                asking_price INTEGER NOT NULL,
                current_offer INTEGER NOT NULL,
                max_budget INTEGER NOT NULL,
                round_number INTEGER NOT NULL DEFAULT 0,
                messages JSONB NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Deals table (scored listings)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                listing_id TEXT PRIMARY KEY REFERENCES listings(id),
                ebay_avg_price INTEGER,
                profit_estimate INTEGER,
                roi_percent FLOAT,
                deal_rating TEXT NOT NULL,
                why_standout TEXT,
                category TEXT,
                match_score FLOAT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Add description column to listings if it doesn't exist
        try:
            await conn.execute("""
                ALTER TABLE listings ADD COLUMN description TEXT;
            """)
        except Exception:
            pass  # Column already exists
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_deals_rating ON deals(deal_rating);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_deals_profit ON deals(profit_estimate);
        """)
        
        # Search history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                min_price INTEGER,
                max_price INTEGER,
                location TEXT,
                results_count INTEGER NOT NULL,
                searched_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        logger.info("Database tables created/verified")


def get_pg_pool() -> asyncpg.Pool:
    """Get PostgreSQL connection pool"""
    if pg_pool is None:
        raise RuntimeError("Database not initialized")
    return pg_pool


def get_redis() -> redis.Redis:
    """Get Redis client"""
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client
