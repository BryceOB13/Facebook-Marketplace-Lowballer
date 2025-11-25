# Facebook Marketplace Deal Scout - MVP Build Prompts

**Target: Functional MVP Tonight**
**Stack: Python FastAPI + Next.js + Shadcn UI + Chrome DevTools MCP**
**Approach: Sequential prompts, each builds on the previous**

---

## PROMPT 0: Project Initialization

```
Create a monorepo for "deal-scout" with the following structure:

Root level:
- turbo.json for Turborepo
- pnpm-workspace.yaml
- docker-compose.yml (PostgreSQL + Redis)
- .env.example

apps/web/ - Next.js 14 with App Router:
- TypeScript strict mode
- Tailwind CSS
- Shadcn UI (initialize with: npx shadcn@latest init)
- Install these shadcn components: button, card, input, table, badge, dialog, tabs, toast

apps/api/ - Python FastAPI:
- pyproject.toml with dependencies: fastapi, uvicorn, pydantic, aiohttp, beautifulsoup4, redis, asyncpg, python-dotenv
- src/main.py with CORS enabled for localhost:3000
- src/models/ directory
- src/routers/ directory  
- src/services/ directory

.kiro/ directory:
- settings/mcp.json with Chrome DevTools MCP configuration
- specs/deal-scout/requirements.md (empty for now)
- specs/deal-scout/tasks.md (empty for now)

Initialize git, create .gitignore for node_modules, __pycache__, .env, .next, venv

The Chrome DevTools MCP config should be:
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest", "--headless=false"]
    }
  }
}
```

---

## PROMPT 1: Data Models & Database Schema

```
In apps/api/src/models/, create Pydantic models and database schema:

listing.py:
- Listing model with fields: id (str), title (str), price (str), price_value (int nullable), location (str nullable), image_url (str nullable), url (str), seller_name (str nullable), scraped_at (datetime), match_score (float nullable), match_reason (str nullable)
- ListingCreate for input validation
- ListingResponse for API responses

deal.py:
- Deal model extending Listing with: ebay_avg_price (float nullable), profit_estimate (float nullable), roi_percent (float nullable), deal_rating (enum: HOT, GOOD, FAIR, PASS), is_new (bool), price_changed (bool), old_price (str nullable)

negotiation.py:
- NegotiationState enum: IDLE, COMPOSING, AWAITING_RESPONSE, PROCESSING, COUNTEROFFER, ACCEPTED, REJECTED, ABANDONED
- Negotiation model: id, listing_id, state (NegotiationState), asking_price (int), current_offer (int), max_budget (int), round_number (int), messages (list of dicts with role/content/timestamp), created_at, updated_at

search.py:
- SearchQuery model: query (str), min_price (int nullable), max_price (int nullable), location (str nullable), category (str nullable)
- SearchResult model: listings (list[Listing]), total_count (int), query_variations (list[str])

Create apps/api/src/db.py with:
- Async PostgreSQL connection using asyncpg
- Redis connection for caching
- Connection pool management
- Database initialization function that creates tables if not exist

SQL schema should support:
- listings table with indexes on price_value, scraped_at, location
- negotiations table with foreign key to listings
- search_history table for tracking queries
```

---

## PROMPT 2: Multi-Query Search Engine (Cost Optimized)

```
Create apps/api/src/services/search/query_generator.py:

Implement a QueryGenerator class that takes a user's search term and generates 3-5 query variations WITHOUT using any LLM calls. Use pure Python logic:

Methods:
- generate_variations(query: str) -> list[str]: Returns variations like:
  - Original query
  - Query with common synonyms (use a hardcoded synonym dict for common marketplace terms)
  - Query with/without brand names extracted
  - Plural/singular variations
  - Common misspellings for that category

- get_category_keywords(query: str) -> list[str]: Map queries to Facebook Marketplace categories using keyword matching (electronics, vehicles, furniture, etc.)

Example: "macbook pro" -> ["macbook pro", "mac book pro", "apple macbook", "macbook", "macbook pro laptop"]

This is LOCAL ONLY - no API calls. The goal is to maximize search coverage without cost.

Create apps/api/src/services/search/url_builder.py:
- Build Facebook Marketplace search URLs with proper encoding
- Support filters: minPrice, maxPrice, daysSinceListed, deliveryMethod
- Location-based URL construction (marketplace/{location}/search)

Create apps/api/src/services/search/search_orchestrator.py:
- SearchOrchestrator class that:
  - Takes a SearchQuery
  - Generates query variations
  - Builds URLs for each variation
  - Returns list of URLs to scrape
  - Deduplicates results by listing ID
  - Caches results in Redis with 5-minute TTL
```

---

## PROMPT 3: Browser Automation with Chrome DevTools MCP

```
Create apps/api/src/services/browser/mcp_client.py:

Implement ChromeMCPClient class that wraps Chrome DevTools MCP calls:

class ChromeMCPClient:
    def __init__(self, mcp_endpoint: str = "http://localhost:9222"):
        self.endpoint = mcp_endpoint
        self.session_cookies = None
    
    async def navigate(self, url: str, wait_for: str = "load") -> bool
    async def execute_script(self, script: str) -> Any
    async def click(self, selector: str) -> bool
    async def type_text(self, selector: str, text: str) -> bool
    async def scroll_page(self, iterations: int = 3, delay_ms: int = 2000) -> bool
    async def get_page_html(self) -> str
    async def save_cookies(self, path: str) -> bool
    async def load_cookies(self, path: str) -> bool

Key implementation details:
- All methods should have try/except with logging
- Include random delays between 1-3 seconds for human-like behavior
- scroll_page should scroll to bottom, wait, repeat
- execute_script should handle JSON responses

Create apps/api/src/services/browser/extractor.py:

JavaScript extraction script (as Python string) that runs in browser:
- Find all listing links matching /marketplace/item/
- Extract: id (from URL), title, price, location, image_url, seller info
- Return as JSON array
- Use stable selectors (aria-labels, data attributes, URL patterns)
- NOT obfuscated class names

The extractor should:
- Handle Facebook's dynamic loading
- Filter out ads and sponsored content
- Return at least: id, title, price, url (others optional)

Create apps/api/src/services/browser/scraper.py:

MarketplaceScraper class:
- Uses ChromeMCPClient
- Implements search_listings(url: str) -> list[Listing]
- Handles login detection (if login modal appears, pause and notify)
- Rate limiting: max 10 pages per hour, 3-7 second delays
- Returns parsed Listing objects
```

---

## PROMPT 4: Deal Scoring & Reseller Mode (No External APIs for MVP)

```
Create apps/api/src/services/reseller/scorer.py:

Implement DealScorer class with LOCAL-ONLY scoring (no eBay API for MVP):

class DealScorer:
    # Hardcoded price reference data for common flip categories
    REFERENCE_PRICES = {
        "iphone 13": {"low": 350, "avg": 450, "high": 550},
        "iphone 14": {"low": 450, "avg": 550, "high": 700},
        "ps5": {"low": 350, "avg": 400, "high": 450},
        "nintendo switch": {"low": 180, "avg": 220, "high": 280},
        "macbook air m1": {"low": 600, "avg": 750, "high": 900},
        "macbook pro m1": {"low": 800, "avg": 1000, "high": 1200},
        # Add 20+ more common flip items
    }
    
    def score_listing(self, listing: Listing) -> Deal:
        # 1. Try to match listing title to reference prices
        # 2. Calculate potential profit margin
        # 3. Apply scoring weights:
        #    - Price vs reference: 40%
        #    - Title keyword quality: 20%
        #    - Has images: 15%
        #    - Location (local = better): 15%
        #    - Listing age: 10%
        # 4. Return Deal with rating (HOT/GOOD/FAIR/PASS)
    
    def calculate_profit(self, buy_price: int, category: str) -> dict:
        # Calculate after Facebook's 5% fee
        # Return: net_profit, roi_percent, break_even
    
    def match_to_category(self, title: str) -> str | None:
        # Fuzzy match title to REFERENCE_PRICES keys
        # Use simple keyword matching, no ML

Create apps/api/src/services/reseller/hot_deals.py:

HotDealDetector class:
- filter_hot_deals(listings: list[Listing]) -> list[Deal]: Score all and return only HOT/GOOD
- get_trending_categories() -> list[str]: Return hardcoded list of currently hot flip categories
- generate_why_standout(deal: Deal) -> str: Generate human-readable explanation like "42% below typical price" or "High-demand item, fast seller"

The "why it stands out" should be templated strings, NOT LLM generated:
- "{percent}% below average {category} price"
- "Priced ${amount} under market value"
- "Hot category - {category} items sell within {days} days"
- "Rare find: {feature} at this price point"
```

---

## PROMPT 5: Lowball Mode - Negotiation State Machine

```
Create apps/api/src/services/negotiation/state_machine.py:

Implement a simple state machine for negotiations (no XState, pure Python):

class NegotiationStateMachine:
    STATES = ["idle", "composing", "sent", "awaiting", "countering", "accepted", "rejected", "abandoned"]
    
    def __init__(self, listing: Listing, max_budget: int):
        self.listing = listing
        self.asking_price = listing.price_value
        self.max_budget = max_budget
        self.current_offer = 0
        self.state = "idle"
        self.round = 0
        self.messages = []
    
    def start(self) -> dict:
        # Calculate initial offer at 65% of asking
        # Transition to "composing"
        # Return: state, suggested_offer, suggested_message
    
    def send_offer(self, offer: int, message: str) -> dict:
        # Record the offer
        # Transition to "awaiting"
        # Return updated state
    
    def receive_response(self, seller_message: str, seller_counter: int | None) -> dict:
        # Parse if it's acceptance, rejection, or counter
        # If counter: transition to "countering", calculate new offer
        # Use decreasing concession: round 1 = 50% of gap, round 2 = 40%, etc.
        # Return: state, recommended_action, suggested_counter
    
    def get_state(self) -> dict:
        # Return full negotiation state for UI

Create apps/api/src/services/negotiation/templates.py:

Message templates (pure string formatting, no LLM):

TEMPLATES = {
    "initial_offer": "Hi! I'm interested in your {title}. Would you consider ${offer}? I can pick up today/tomorrow and pay cash.",
    
    "counter_offer": "Thanks for getting back to me! ${seller_counter} is a bit above my budget. Would ${new_offer} work? That's only ${gap} apart.",
    
    "final_offer": "I appreciate the back and forth! ${final_offer} is the best I can do. Let me know if that works.",
    
    "accept": "Great, ${price} works for me! When's a good time to pick up?",
    
    "walk_away": "Thanks for your time, but I'll have to pass at that price. Good luck with the sale!"
}

def compose_message(template_key: str, context: dict) -> str:
    return TEMPLATES[template_key].format(**context)

Create apps/api/src/services/negotiation/manager.py:

NegotiationManager class:
- create_negotiation(listing_id: str, max_budget: int) -> Negotiation
- get_negotiation(negotiation_id: str) -> Negotiation
- list_active_negotiations() -> list[Negotiation]
- update_state(negotiation_id: str, action: str, data: dict) -> Negotiation
- Store negotiations in PostgreSQL
```

---

## PROMPT 6: FastAPI Routes

```
Create apps/api/src/routers/search.py:

@router.post("/search")
async def search_marketplace(query: SearchQuery) -> SearchResult:
    # 1. Generate query variations
    # 2. Build URLs
    # 3. Check Redis cache first
    # 4. If not cached, scrape each URL
    # 5. Deduplicate by listing ID
    # 6. Score all listings
    # 7. Cache results
    # 8. Return with query_variations included

@router.get("/search/suggestions")
async def get_suggestions(q: str) -> list[str]:
    # Return query variations for autocomplete

Create apps/api/src/routers/deals.py:

@router.get("/deals")
async def list_deals(rating: str = None, limit: int = 50) -> list[Deal]:
    # Return scored deals, optionally filtered by rating

@router.get("/deals/{listing_id}")
async def get_deal(listing_id: str) -> Deal:
    # Return single deal with full details

@router.post("/deals/{listing_id}/track")
async def track_deal(listing_id: str) -> dict:
    # Add to tracked deals for price monitoring

Create apps/api/src/routers/negotiations.py:

@router.post("/negotiations")
async def start_negotiation(listing_id: str, max_budget: int) -> Negotiation:
    # Create new negotiation state machine

@router.get("/negotiations")
async def list_negotiations(state: str = None) -> list[Negotiation]:
    # List all negotiations, optionally filter by state

@router.get("/negotiations/{negotiation_id}")
async def get_negotiation(negotiation_id: str) -> Negotiation:
    # Get full negotiation details with message history

@router.post("/negotiations/{negotiation_id}/send")
async def send_offer(negotiation_id: str, offer: int, message: str) -> Negotiation:
    # Send offer, update state

@router.post("/negotiations/{negotiation_id}/response")
async def record_response(negotiation_id: str, seller_message: str, seller_counter: int = None) -> Negotiation:
    # Record seller response, get recommended action

Create apps/api/src/routers/websocket.py:

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accept connection
    # Subscribe to Redis pub/sub channel "deal-scout:events"
    # Forward events to client: new_deal, price_change, negotiation_update
    # Handle client messages for real-time actions

Update apps/api/src/main.py:
- Include all routers
- Add startup event to initialize DB and Redis
- Add CORS for localhost:3000
- Health check endpoint at /health
```

---

## PROMPT 7: Next.js Frontend - Core Layout

```
In apps/web/, create the dashboard layout:

app/layout.tsx:
- Dark mode by default (Shadcn dark theme)
- Sidebar navigation with links: Dashboard, Search, Deals, Negotiations, Settings
- Use Shadcn's Sidebar component if available, otherwise create simple nav
- Toast provider for notifications
- WebSocket connection provider (context)

app/page.tsx (Dashboard):
- Summary cards at top:
  - Total Deals Found (today)
  - HOT Deals Active
  - Active Negotiations
  - Estimated Profit (from tracked deals)
- Recent deals table (last 10)
- Active negotiations list (last 5)
- Quick search bar

app/search/page.tsx:
- Large search input with placeholder "Search marketplace (e.g., 'macbook pro', 'ps5')"
- Filter controls: Min Price, Max Price, Location dropdown
- "Search" button
- Results grid showing listing cards
- Each card shows: image, title, price, location, deal rating badge, "why it stands out" text
- Actions per card: "Track", "Start Negotiation", "View on Facebook"

app/deals/page.tsx:
- Tabs: All, HOT, GOOD, FAIR, Tracked
- Data table with columns: Title, Price, Rating, Profit Est., Location, Actions
- Sortable by price, rating, profit
- Filterable by rating
- Bulk actions: Track selected, Export CSV

app/negotiations/page.tsx:
- List of negotiation cards
- Each card shows: Listing title, Current state badge, Your offer, Seller counter (if any), Message count
- Click to expand and see full message history
- Action buttons based on state: Send Offer, Counter, Accept, Walk Away

Create components/ui/ (if not from shadcn):
- DealCard.tsx - Card component for displaying a deal
- NegotiationCard.tsx - Card for negotiation status
- StatusBadge.tsx - Badge showing deal rating or negotiation state
- PriceDisplay.tsx - Formatted price with optional comparison
- WhyStandout.tsx - Highlighted text explaining deal value
```

---

## PROMPT 8: Next.js Frontend - API Integration & Real-time

```
Create apps/web/lib/api.ts:

API client using fetch (no external deps):

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  search: async (query: SearchQuery): Promise<SearchResult> => {
    const res = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(query)
    });
    return res.json();
  },
  
  getDeals: async (rating?: string): Promise<Deal[]> => {...},
  getDeal: async (id: string): Promise<Deal> => {...},
  trackDeal: async (id: string): Promise<void> => {...},
  
  startNegotiation: async (listingId: string, maxBudget: number): Promise<Negotiation> => {...},
  getNegotiations: async (): Promise<Negotiation[]> => {...},
  sendOffer: async (negId: string, offer: number, message: string): Promise<Negotiation> => {...},
  recordResponse: async (negId: string, message: string, counter?: number): Promise<Negotiation> => {...},
};

Create apps/web/lib/websocket.ts:

WebSocket hook for real-time updates:

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLastEvent(data);
      
      // Handle different event types
      if (data.type === 'new_deal') toast({ title: 'New HOT deal found!' });
      if (data.type === 'price_drop') toast({ title: 'Price dropped!' });
    };
    
    return () => ws.close();
  }, []);
  
  return { connected, lastEvent };
}

Create apps/web/lib/stores.ts:

Simple Zustand store (or use React context if you prefer):

interface DealStore {
  deals: Deal[];
  setDeals: (deals: Deal[]) => void;
  addDeal: (deal: Deal) => void;
  trackedIds: Set<string>;
  trackDeal: (id: string) => void;
}

// Similar for negotiations store

Create apps/web/hooks/useSearch.ts:

Custom hook for search with loading state:

export function useSearch() {
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const search = async (query: SearchQuery) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(query);
      setResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  
  return { results, loading, error, search };
}
```

---

## PROMPT 9: Wire It All Together

```
Final integration tasks:

1. Update apps/api/src/main.py to:
   - Initialize database tables on startup
   - Initialize Redis connection pool
   - Add background task that publishes events to Redis pub/sub
   - Log all requests for debugging

2. Create apps/api/src/services/event_bus.py:
   - publish_event(event_type: str, data: dict) -> None
   - Events: new_listing, price_change, deal_scored, negotiation_update
   - Publishes to Redis channel "deal-scout:events"

3. Create docker-compose.yml:
   version: '3.8'
   services:
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: dealscout
         POSTGRES_USER: dealscout
         POSTGRES_PASSWORD: localdev
       ports:
         - "5432:5432"
     redis:
       image: redis:7
       ports:
         - "6379:6379"

4. Create apps/web/app/api/health/route.ts:
   - Proxy health check to backend
   - Used for deployment verification

5. Create start-dev.sh script:
   #!/bin/bash
   # Start Chrome with remote debugging
   # macOS:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &
   
   # Start docker services
   docker-compose up -d
   
   # Start API
   cd apps/api && uvicorn src.main:app --reload --port 8000 &
   
   # Start frontend
   cd apps/web && pnpm dev &
   
   echo "Deal Scout running at http://localhost:3000"

6. Create README.md with:
   - Setup instructions
   - How to run locally
   - Architecture overview
   - API endpoints documentation
```

---

## PROMPT 10: Test the MVP Flow

```
Create a test script apps/api/tests/test_flow.py:

Test the complete MVP flow:

1. Test query generation:
   - Input: "macbook pro"
   - Assert: Returns 3-5 variations
   - Assert: No API calls made

2. Test URL building:
   - Input: query="iphone", min_price=200, max_price=500
   - Assert: Valid Facebook Marketplace URL with encoded params

3. Test deal scoring:
   - Input: Listing with title="iPhone 14 Pro", price="$400"
   - Assert: Returns Deal with rating (should be HOT based on reference prices)
   - Assert: match_reason is populated

4. Test negotiation flow:
   - Create negotiation with asking_price=500, max_budget=400
   - Assert: Initial offer is ~325 (65% of asking)
   - Simulate counter at 450
   - Assert: New offer uses decreasing concession
   - Assert: Eventually reaches max_budget or walks away

5. Test message templates:
   - Assert: All templates produce valid strings
   - Assert: No placeholder variables remain

Create apps/web/app/test/page.tsx:

Simple test page that:
- Has a "Test Search" button that searches for "test item"
- Displays raw API response
- Shows connection status to WebSocket
- Has "Test Negotiation" that creates a mock negotiation

Run the test:
1. Start docker-compose
2. Start API server
3. Start Chrome with debugging
4. Open http://localhost:3000/test
5. Click test buttons and verify responses
```

---

## Quick Reference: Run Order

```bash
# Terminal 1: Start dependencies
docker-compose up

# Terminal 2: Start Chrome with debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Terminal 3: Start API
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -e .
uvicorn src.main:app --reload --port 8000

# Terminal 4: Start frontend
cd apps/web
pnpm install
pnpm dev

# Open browser
open http://localhost:3000
```

---

## Cost Optimization Checklist (Built Into Prompts)

✅ Query generation is LOCAL (no LLM)
✅ Deal scoring uses hardcoded reference prices (no LLM)
✅ Message templates are string formatting (no LLM)
✅ "Why it stands out" is templated (no LLM)
✅ Only browser automation uses MCP (minimal LLM)
✅ Results cached in Redis (5 min TTL)
✅ Rate limited (10 pages/hour)

**Total LLM cost for MVP: Near zero** - only Chrome DevTools MCP for navigation
