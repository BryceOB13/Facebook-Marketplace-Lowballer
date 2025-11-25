"""
FastAPI main application for Deal Scout.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.db import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Deal Scout API...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Deal Scout API...")
    await close_db()


app = FastAPI(
    title="Deal Scout API",
    description="Facebook Marketplace deal finder and negotiation assistant",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Deal Scout API",
        "docs": "/docs",
        "health": "/health"
    }


# Import and include routers
from src.routers import search, deals, negotiations

app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(deals.router, prefix="/api", tags=["deals"])
app.include_router(negotiations.router, prefix="/api", tags=["negotiations"])
