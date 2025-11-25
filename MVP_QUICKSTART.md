# Deal Scout MVP - Quick Start Guide

## 🎉 MVP Complete!

Full-stack Facebook Marketplace automation with AI-powered search, deal scoring, and negotiation.

## Architecture

**Backend (FastAPI + Python)**
- PostgreSQL for data persistence
- Redis for caching
- Claude Haiku for all AI operations
- Chrome DevTools for browser automation

**Frontend (Next.js 14 + TypeScript)**
- Tailwind CSS + Shadcn UI (dark mode)
- Real-time updates
- Responsive design

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Google Chrome
- Anthropic API key

## Setup

### 1. Environment Variables

```bash
# Copy example env
cp .env.example .env

# Add your API key
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
```

### 2. Start Services

```bash
# Start PostgreSQL + Redis
docker-compose up -d

# Wait for services to be ready
sleep 5
```

### 3. Start Chrome with Remote Debugging

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/.chrome-dealscout-profile \
  --disable-blink-features=AutomationControlled &

# Linux
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/.chrome-dealscout-profile \
  --disable-blink-features=AutomationControlled &
```

**Important:** Log into Facebook in this Chrome window!

### 4. Start Backend

```bash
cd apps/api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Run server
uvicorn src.main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

### 5. Start Frontend

```bash
cd apps/web

# Install dependencies
pnpm install  # or npm install

# Create env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run dev server
pnpm dev  # or npm run dev
```

Frontend will be available at: http://localhost:3000

## Usage

### 1. Search for Deals

1. Go to http://localhost:3000/search
2. Enter search query (e.g., "macbook pro", "ps5")
3. Optionally set price range and location
4. Click "Search Marketplace"

**What happens:**
- Claude Haiku generates 3-5 query variations (~$0.001)
- Chrome scrapes each variation
- Results are deduplicated and cached (5min)
- Saved to PostgreSQL

### 2. Score Deals

1. Go to http://localhost:3000/deals
2. Filter by rating (HOT, GOOD, FAIR)
3. View deal cards with profit estimates

**What happens:**
- Claude Haiku evaluates each listing (~$0.002)
- Estimates market value
- Calculates profit after fees
- Generates "why it stands out" explanation

### 3. Start Negotiation

1. Click "Negotiate" on any deal
2. Set your max budget
3. Review AI-generated initial offer message
4. Send offer

**What happens:**
- State machine calculates 65% initial offer
- Claude Haiku generates personalized message (~$0.0002)
- Tracks negotiation state

### 4. Handle Seller Response

1. Go to http://localhost:3000/negotiations
2. Click on active negotiation
3. Enter seller's response
4. Review AI-suggested counter offer
5. Send counter

**What happens:**
- Claude Haiku analyzes seller intent (~$0.0001)
- Calculates counter using decreasing concession
- Generates contextual message (~$0.0002)

## Cost Breakdown

**Per Listing (Full Workflow):**
- Query generation: $0.001
- Deal scoring: $0.002
- Negotiation (5 rounds): $0.0015
- **Total: ~$0.005 per listing**

**Monthly Estimate (100 listings):**
- 100 searches × $0.001 = $0.10
- 100 scorings × $0.002 = $0.20
- 20 negotiations × $0.0015 = $0.03
- **Total: ~$0.33/month**

## Features

✅ **Search**
- AI-powered query expansion
- Multi-query scraping
- Redis caching
- Price/location filters

✅ **Deal Scoring**
- LLM market analysis
- Profit estimation
- ROI calculation
- Rating system (HOT/GOOD/FAIR/PASS)

✅ **Negotiation**
- AI message generation
- Response analysis
- Decreasing concession strategy
- State machine tracking

✅ **Anti-Detection**
- Human-like delays (3-7s)
- Random scrolling
- Rate limiting (10 pages/hour)
- Session persistence

## Troubleshooting

### Chrome not connecting
```bash
# Check if Chrome is running
curl http://localhost:9222/json/version

# Restart Chrome with debugging
pkill -f "Chrome.*9222"
# Then run Chrome command again
```

### Database connection failed
```bash
# Check Docker services
docker-compose ps

# Restart services
docker-compose restart
```

### API key not working
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### Frontend can't connect to backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS settings in apps/api/src/main.py
# Should allow http://localhost:3000
```

## Development

### Run tests
```bash
cd apps/api
pytest tests/ -v
```

### View logs
```bash
# Backend logs
tail -f apps/api/logs/*.log

# Docker logs
docker-compose logs -f
```

### Database access
```bash
# Connect to PostgreSQL
docker exec -it dealscout-postgres psql -U dealscout

# View tables
\dt

# Query listings
SELECT id, title, price FROM listings LIMIT 10;
```

## Production Deployment

See `docs/ARCHITECTURE.md` for production deployment guide including:
- Prompt caching for 90% savings
- Batch API for 50% discount
- Model routing (Haiku vs Sonnet)
- Horizontal scaling

## Next Steps

1. **Add WebSocket support** for real-time updates
2. **Implement price tracking** for monitored deals
3. **Add email notifications** for hot deals
4. **Build mobile app** with React Native
5. **Add eBay API integration** for real market data

## Support

- API Docs: http://localhost:8000/docs
- Architecture: `docs/ARCHITECTURE.md`
- MVP Guide: `docs/MVP_BUILD_GUIDE.md`

---

**Built with:**
- FastAPI + PostgreSQL + Redis
- Next.js 14 + Tailwind CSS
- Claude Haiku (Anthropic)
- Chrome DevTools Protocol
