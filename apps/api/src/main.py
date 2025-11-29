"""
FastAPI main application for Deal Scout.
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
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
        "health": "/health",
        "demo": "/demo"
    }


@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Serve the demo page"""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deal Scout - View Deal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 40px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .card { background: white; border-radius: 12px; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .input-group { margin-bottom: 20px; }
        .input-group label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
        .input-group input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; }
        .input-group input:focus { outline: none; border-color: #667eea; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 14px 32px; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; width: 100%; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .loading { text-align: center; padding: 40px; display: none; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .result { display: none; }
        .result.show { display: block; }
        .rating-badge { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: 700; font-size: 0.9rem; margin-bottom: 15px; }
        .rating-HOT { background: #ff4444; color: white; }
        .rating-GOOD { background: #00C851; color: white; }
        .rating-FAIR { background: #ffbb33; color: white; }
        .rating-PASS { background: #999; color: white; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric { background: #f8f9fa; padding: 15px; border-radius: 8px; }
        .metric-label { font-size: 0.85rem; color: #666; margin-bottom: 5px; }
        .metric-value { font-size: 1.5rem; font-weight: 700; color: #333; }
        .action-item { padding: 12px; background: #f8f9fa; border-left: 4px solid #667eea; margin-bottom: 10px; border-radius: 4px; }
        .error { background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin-top: 20px; display: none; }
        .error.show { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Deal Scout</h1>
            <p>AI-Powered Facebook Marketplace Deal Analyzer</p>
        </div>
        <div class="card">
            <div class="input-group">
                <label for="url">Facebook Marketplace Listing URL</label>
                <input type="url" id="url" placeholder="https://www.facebook.com/marketplace/item/123456789">
            </div>
            <button class="btn" onclick="analyzeDeal()">Analyze Deal</button>
            <div class="loading" id="loading"><div class="spinner"></div><p>Analyzing deal...</p></div>
            <div class="error" id="error"></div>
        </div>
        <div class="card result" id="result"><div id="resultContent"></div></div>
    </div>
    <script>
        async function analyzeDeal() {
            const url = document.getElementById('url').value.trim();
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');
            const result = document.getElementById('result');
            const btn = document.querySelector('.btn');
            if (!url) { showError('Please enter a Facebook Marketplace URL'); return; }
            loading.style.display = 'block';
            error.classList.remove('show');
            result.classList.remove('show');
            btn.disabled = true;
            try {
                const response = await fetch('/api/deals/view?url=' + encodeURIComponent(url), { method: 'POST' });
                if (!response.ok) { const errorData = await response.json(); throw new Error(errorData.detail || 'Failed to analyze deal'); }
                const data = await response.json();
                displayResult(data);
            } catch (err) { showError(err.message); }
            finally { loading.style.display = 'none'; btn.disabled = false; }
        }
        function displayResult(data) {
            const result = document.getElementById('result');
            const content = document.getElementById('resultContent');
            const listing = data.listing;
            const analysis = data.analysis;
            const negotiation = data.negotiation_strategy;
            const actions = data.action_items;
            let html = '<div class="rating-badge rating-' + analysis.rating + '">' + analysis.rating + '</div>';
            html += '<h2>' + listing.title + '</h2>';
            html += '<p style="color: #666; margin: 10px 0;">$' + listing.price.toFixed(0) + '</p>';
            html += '<div class="metrics">';
            html += '<div class="metric"><div class="metric-label">Deal Score</div><div class="metric-value">' + analysis.score.toFixed(1) + '/100</div></div>';
            html += '<div class="metric"><div class="metric-label">Profit Estimate</div><div class="metric-value">$' + analysis.profit_estimate.toFixed(0) + '</div></div>';
            html += '<div class="metric"><div class="metric-label">ROI</div><div class="metric-value">' + analysis.roi_percent.toFixed(1) + '%</div></div>';
            html += '<div class="metric"><div class="metric-label">eBay Avg</div><div class="metric-value">$' + analysis.ebay_avg_price.toFixed(0) + '</div></div>';
            html += '</div>';
            html += '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;"><strong>Analysis:</strong> ' + analysis.reason + '</div>';
            if (negotiation) {
                html += '<div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">';
                html += '<h3 style="margin-bottom: 10px;">💰 Negotiation Strategy</h3>';
                html += '<p><strong>Initial Offer:</strong> $' + negotiation.initial_offer.toFixed(0) + '</p>';
                html += '<p><strong>Target Price:</strong> $' + negotiation.target_price.toFixed(0) + '</p>';
                html += '<p><strong>Walk Away Above:</strong> $' + negotiation.walk_away_price.toFixed(0) + '</p></div>';
            }
            if (actions && actions.length > 0) {
                html += '<div class="action-items"><h3 style="margin-bottom: 15px;">📋 Next Steps</h3>';
                actions.forEach(function(action) { html += '<div class="action-item">' + action + '</div>'; });
                html += '</div>';
            }
            content.innerHTML = html;
            result.classList.add('show');
        }
        function showError(message) { const error = document.getElementById('error'); error.textContent = message; error.classList.add('show'); }
        document.getElementById('url').addEventListener('keypress', function(e) { if (e.key === 'Enter') analyzeDeal(); });
    </script>
</body>
</html>'''
    return html


# Import and include routers
from src.routers import search, deals, negotiations, ebay_notifications

app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(deals.router, prefix="/api", tags=["deals"])
app.include_router(negotiations.router, prefix="/api", tags=["negotiations"])
app.include_router(ebay_notifications.router, prefix="/api", tags=["ebay"])
