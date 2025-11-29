# eBay Browse API Integration Guide

## Overview

The Deal Scout now integrates with eBay's Browse API to provide:
- **Real-time market price validation** from eBay sold/active listings
- **AI-powered deal scoring** combining market data with Claude analysis
- **Profit estimation** with platform fees and shipping costs
- **Comparable item search** for manual validation

## Setup

### 1. Get eBay API Credentials

1. Visit [eBay Developers Program](https://developer.ebay.com/)
2. Create an account and register a new application
3. Get your **Client ID** and **Client Secret**
4. Add to `.env`:

```bash
EBAY_CLIENT_ID=your_client_id_here
EBAY_CLIENT_SECRET=your_client_secret_here
```

### 2. Install Dependencies

```bash
pip install aiohttp anthropic
```

## API Endpoints

### Analyze Deal

**POST** `/deals/analyze`

Analyzes a Facebook Marketplace listing for resale potential.

**Request:**
```json
{
  "title": "iPhone 13 Pro 256GB",
  "price": 450,
  "condition": "USED",
  "description": "Excellent condition, no scratches, includes charger",
  "use_ai": true
}
```

**Response:**
```json
{
  "deal_rating": "HOT",
  "profit_estimate": 125.50,
  "roi_percent": 27.9,
  "ebay_avg_price": 625.00,
  "ebay_median_price": 599.00,
  "confidence": "HIGH",
  "reason": "Strong deal: 25% below market, $125 profit potential (28% ROI)",
  "comparable_count": 18,
  "score": 85.3
}
```

### Search eBay

**POST** `/deals/ebay/search`

Search eBay for comparable items.

**Request:**
```json
{
  "query": "MacBook Pro 2021",
  "condition": "USED",
  "price_min": 800,
  "price_max": 1200,
  "limit": 20
}
```

### Get Price Statistics

**GET** `/deals/ebay/price-stats?query=iPad Air 2022&condition=USED`

Returns average, median, min, max prices from eBay.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Deal Analysis Flow                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Facebook Listing → DealAnalyzer                      │
│                                                          │
│  2. EbayBrowseClient.search_items()                      │
│     ├─ OAuth2 token management                           │
│     ├─ Search with filters                               │
│     └─ 1-hour result caching                             │
│                                                          │
│  3. Calculate base score (multi-factor)                  │
│     ├─ Price discount vs market (40%)                    │
│     ├─ ROI potential (30%)                               │
│     ├─ Absolute profit (20%)                             │
│     └─ Market confidence (10%)                           │
│                                                          │
│  4. Optional: Claude Haiku AI analysis                   │
│     ├─ Condition assessment                              │
│     ├─ Red flag detection                                │
│     └─ Demand indicators                                 │
│                                                          │
│  5. Return rating: HOT/GOOD/FAIR/PASS                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Cost Optimization

### eBay API
- **Free tier**: 5,000 calls/day
- **Caching**: 1-hour TTL reduces redundant calls
- **Batch operations**: Analyze multiple listings efficiently

### Claude AI
- **Model**: Haiku (~$0.001 per analysis)
- **Optional**: Can disable AI for pure market-based scoring
- **Selective use**: Only for high-potential deals

## Usage Examples

### Python Client

```python
from services.ebay import DealAnalyzer

analyzer = DealAnalyzer()

result = await analyzer.analyze_deal(
    listing_title="Sony PS5 Digital Edition",
    listing_price=350,
    listing_condition="USED",
    listing_description="Like new, barely used",
    use_ai=True
)

if result["deal_rating"] == "HOT":
    print(f"🔥 Hot deal! Profit: ${result['profit_estimate']}")
```

### Integration with View Deal

Update `view_deal` function to use eBay analysis:

```python
async def view_deal(listing_url: str):
    # Extract listing details
    listing = await scrape_listing(listing_url)
    
    # Analyze with eBay data
    analysis = await analyzer.analyze_deal(
        listing_title=listing.title,
        listing_price=listing.price,
        listing_condition=listing.condition,
        listing_description=listing.description
    )
    
    # Only proceed if HOT or GOOD
    if analysis["deal_rating"] in ["HOT", "GOOD"]:
        return {
            "should_pursue": True,
            "analysis": analysis,
            "listing": listing
        }
```

## Best Practices

1. **Cache aggressively**: eBay data doesn't change rapidly
2. **Use AI selectively**: Enable only for promising deals (score > 50)
3. **Batch analyze**: Process multiple listings together
4. **Monitor rate limits**: Stay within eBay's 5K/day free tier
5. **Fallback gracefully**: Handle API failures with basic scoring

## Troubleshooting

### "Failed to get eBay token"
- Verify `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` in `.env`
- Check credentials are for Production (not Sandbox)

### "No comparable eBay listings found"
- Item may be too niche or misspelled
- Try broader search terms
- Check if category is supported

### High API costs
- Reduce `use_ai=True` frequency
- Increase cache TTL
- Use batch endpoints

## Next Steps

1. **Integrate with scraper**: Auto-analyze all scraped listings
2. **Add notifications**: Alert on HOT deals via webhook
3. **Historical tracking**: Store price trends in TimescaleDB
4. **Category optimization**: Fine-tune scoring per category
