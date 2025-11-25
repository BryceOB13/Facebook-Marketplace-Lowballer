# Facebook Marketplace Deal Scout: Complete Architecture and Implementation Strategy

The Deal Scout automation agent can achieve **60-80% cost reduction** through tiered model routing, prompt caching, and batching—while a modular architecture separates browser automation, negotiation state machines, and price arbitrage into independent services. This comprehensive guide provides the complete blueprint from cost optimization through Kiro spec-driven development.

## The core problem: computational expense without output

Your current architecture suffers from a common anti-pattern in AI browser automation: sending full DOM context to expensive models for every interaction. The solution combines **three cost levers**: intelligent model routing (Haiku for filtering, Sonnet for decisions), aggressive prompt caching (90% savings on repeated context), and pre-filtering data locally before any API call. Combined with the Batch API's 50% discount for non-urgent tasks, realistic production savings reach **60-80%**.

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FACEBOOK MARKETPLACE DEAL SCOUT                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           NEXT.JS DASHBOARD                          │   │
│  │  Real-time WebSocket ← Redis Pub/Sub ← Agent Events                  │   │
│  │  Shadcn UI: Data Tables | Status Cards | Profit Charts               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      ↕ REST/WS                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         PYTHON FASTAPI BACKEND                        │   │
│  │                                                                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   Model     │  │   Prompt    │  │  Semantic   │  │    Task     │  │   │
│  │  │   Router    │→ │   Cache     │→ │   Cache     │→ │   Queue     │  │   │
│  │  │ Haiku/Sonnet│  │ (Anthropic) │  │ (Redis+FAISS)│  │   (Batch)   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  │                                                                        │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │   │
│  │  │                    CHROME DEVTOOLS MCP                          │  │   │
│  │  │  Session Manager | Cookie Persistence | Anti-Detection          │  │   │
│  │  │  Ghost Cursor (human-like) | Stealth Plugin | Proxy Rotation    │  │   │
│  │  └─────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                        │   │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐  │   │
│  │  │   LOWBALL MODE    │  │   RESELLER MODE   │  │  EXTRACTION      │  │   │
│  │  │   (Negotiation)   │  │   (Hot Flip)      │  │  ENGINE          │  │   │
│  │  │                   │  │                   │  │                  │  │   │
│  │  │ XState Machine    │  │ eBay Sold Lookup  │  │ DOM Parser       │  │   │
│  │  │ Template Engine   │  │ Profit Calculator │  │ Rate Limiter     │  │   │
│  │  │ Intent Classifier │  │ Deal Scorer       │  │ URL Builder      │  │   │
│  │  └───────────────────┘  └───────────────────┘  └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                    │   │
│  │  PostgreSQL (listings, deals) | TimescaleDB (price history)          │   │
│  │  Redis (cache, pub/sub) | SQLite (session cookies)                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost optimization strategies

### Model routing cuts costs by 35-85%

Route simple tasks to Claude Haiku 3 ($0.25/MTok input) and reserve Sonnet ($3/MTok) for complex decisions:

```python
class ModelRouter:
    ROUTING_RULES = {
        "trivial": "claude-haiku-3-20250722",      # $0.25/$1.25 - click, scroll, wait
        "simple": "claude-haiku-4-5-20251022",     # $1/$5 - DOM element identification
        "moderate": "claude-sonnet-4-5-20250929",  # $3/$15 - action planning
        "complex": "claude-opus-4-5-20251124",     # $5/$25 - multi-step reasoning
    }
    
    def route_request(self, task: str) -> str:
        # Free heuristic classification first
        if self._is_simple_action(task):
            return self.ROUTING_RULES["trivial"]
        if self._requires_multi_step_reasoning(task):
            return self.ROUTING_RULES["complex"]
        # Haiku classifier for ambiguous cases (~$0.001 per classification)
        return self._llm_classify(task)
    
    def _is_simple_action(self, task: str) -> bool:
        simple_patterns = ["click", "type", "scroll", "wait", "navigate to"]
        return any(p in task.lower() for p in simple_patterns)
```

### Prompt caching delivers 90% savings on repeated context

Cache system prompts and browser context using Anthropic's built-in caching:

```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": """Browser automation agent for Facebook Marketplace.
        
        CAPABILITIES: click(selector), scroll(direction), type(selector, text)
        OUTPUT: JSON only. {"action": "...", "params": {...}}
        CONSTRAINTS: Single action per response. CSS selectors preferred.""",
        "cache_control": {"type": "ephemeral"}  # 5-minute TTL
    }],
    messages=[{"role": "user", "content": compressed_dom_context}]
)
# Cache reads cost 10% of base price = 90% savings on repeated system prompts
```

### Batch API provides 50% discount for non-urgent tasks

Queue bulk operations like listing evaluations:

```python
batch_requests = [
    {
        "custom_id": f"evaluate_listing_{listing.id}",
        "params": {
            "model": "claude-haiku-4-5-20251022",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": f"Evaluate: {listing.json()}"}]
        }
    }
    for listing in pending_listings
]

batch = client.beta.messages.batches.create(requests=batch_requests)
# Results available within 24 hours at 50% cost reduction
```

### Pre-filter DOM locally before API calls

Reduce token usage by **50-80%** through local HTML processing:

```python
def compress_dom_for_llm(raw_html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Remove non-interactive elements
    for tag in soup.find_all(['script', 'style', 'meta', 'link', 'noscript']):
        tag.decompose()
    
    # Extract only interactive elements
    interactive = soup.find_all(['button', 'input', 'a', 'select', 'textarea'])
    
    # Return compressed representation
    return json.dumps([{
        'tag': el.name,
        'id': el.get('id'),
        'class': el.get('class'),
        'text': el.get_text()[:50],
        'href': el.get('href')
    } for el in interactive[:30]])  # Top 30 elements only
```

### Combined savings estimate

| Strategy | Individual Savings | Combined Effect |
|----------|-------------------|-----------------|
| Model Routing | 35-85% | Multiplicative |
| Prompt Caching | 90% on cache hits | Stacks with routing |
| Batch API | 50% | Stacks with caching |
| DOM Pre-filtering | 50-80% token reduction | Multiplicative |
| **Total Realistic Savings** | **60-80%** | Production deployment |

---

## Chrome DevTools MCP configuration

### Basic MCP setup for Claude Agent SDK

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--headless=false",
        "--viewport=1920x1080"
      ]
    }
  }
}
```

### Anti-detection configuration for Facebook Marketplace

Facebook employs aggressive bot detection. Use these patterns:

```python
# marketplace_scraper.py
import puppeteer_extra
from puppeteer_extra_plugin_stealth import StealthPlugin
from ghost_cursor import createCursor

puppeteer_extra.use(StealthPlugin())

class MarketplaceScraper:
    async def initialize(self):
        self.browser = await puppeteer_extra.launch({
            'headless': False,  # Headed mode for marketplace
            'userDataDir': './chrome-profile-marketplace',  # Persist sessions
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
                f'--proxy-server={self.rotating_proxy}'
            ]
        })
        
        self.page = await self.browser.newPage()
        self.cursor = createCursor(self.page)  # Human-like mouse movements
        
        # Realistic viewport and user agent
        await self.page.setViewport({'width': 1920, 'height': 1080})
        await self.page.setUserAgent(self._random_user_agent())
    
    async def human_click(self, selector: str):
        """Click with Bezier curves and Fitts's Law timing"""
        await self.cursor.click(selector, {
            'hesitate': random.randint(200, 500),  # Delay before click
            'waitForClick': random.randint(50, 150),  # Between mousedown/up
            'moveDelay': random.randint(1000, 2000)  # Post-move delay
        })
    
    async def random_delay(self, min_ms=1000, max_ms=3000):
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)
```

### Session persistence with cookies

```python
class CookieManager:
    def __init__(self, cookies_path='./marketplace_cookies.json'):
        self.cookies_path = cookies_path
    
    async def save(self, page):
        cookies = await page.cookies()
        with open(self.cookies_path, 'w') as f:
            json.dump(cookies, f)
    
    async def load(self, page):
        try:
            with open(self.cookies_path) as f:
                cookies = json.load(f)
            await page.setCookie(*cookies)
            return True
        except FileNotFoundError:
            return False
    
    async def check_session_valid(self, page):
        await page.goto('https://www.facebook.com/marketplace')
        logged_in = await page.querySelector('[aria-label="Your profile"]')
        return logged_in is not None
```

---

## Lowball mode: automated negotiation state machine

### XState-based negotiation flow

```typescript
// negotiation-machine.ts
import { createMachine, assign } from 'xstate';

interface NegotiationContext {
  itemId: string;
  askingPrice: number;
  currentOffer: number;
  maxBudget: number;
  roundNumber: number;
  conversationHistory: Message[];
}

const negotiationMachine = createMachine({
  id: 'negotiation',
  initial: 'idle',
  context: {} as NegotiationContext,
  states: {
    idle: {
      on: { START: { target: 'composing', guard: 'itemAvailable' } }
    },
    composing: {
      entry: assign({
        currentOffer: ({ context }) => context.askingPrice * 0.65  // 35% below asking
      }),
      on: { SEND: 'awaiting_response' }
    },
    awaiting_response: {
      after: {
        86400000: { target: 'retry_scheduled', guard: 'canRetry' },  // 24h
        172800000: 'abandoned'  // 48h final timeout
      },
      on: { RESPONSE: 'processing_response' }
    },
    processing_response: {
      invoke: {
        src: 'analyzeResponse',
        onDone: [
          { target: 'accepted', guard: 'isAcceptance' },
          { target: 'rejected', guard: 'isRejection' },
          { target: 'counteroffer', guard: 'isCounter' }
        ]
      }
    },
    counteroffer: {
      on: {
        ESCALATE: { target: 'escalating', guard: 'withinBudget' },
        WALK_AWAY: 'abandoned'
      }
    },
    escalating: {
      entry: assign({
        currentOffer: ({ context, event }) => 
          Math.min(event.counterPrice * 0.95, context.maxBudget)
      }),
      on: { SEND: 'awaiting_response' }
    },
    accepted: { type: 'final' },
    rejected: { type: 'final' },
    abandoned: { type: 'final' }
  }
});
```

### Dynamic pricing with decreasing concessions

```python
def calculate_counter_offer(context: dict) -> dict:
    """Concession decreases with each round (academic negotiation theory)"""
    seller_price = context['seller_counter']
    my_last_offer = context['current_offer']
    max_budget = context['max_budget']
    round_number = context['round_number']
    
    # Decreasing concession rates per round
    concession_rates = [0.50, 0.40, 0.30, 0.20, 0.15]
    rate = concession_rates[min(round_number, 4)]
    
    gap = seller_price - my_last_offer
    concession = gap * rate
    new_offer = my_last_offer + concession
    
    if new_offer > max_budget:
        if seller_price <= max_budget * 1.05:  # Within 5% of budget
            return {'action': 'FINAL_OFFER', 'amount': max_budget}
        return {'action': 'WALK_AWAY'}
    
    # Check convergence (within 5% of asking)
    if abs(seller_price - new_offer) < context['asking_price'] * 0.05:
        return {'action': 'SPLIT', 'amount': (seller_price + new_offer) / 2}
    
    return {'action': 'COUNTER', 'amount': round(new_offer)}
```

### Message template engine

```python
TEMPLATES = {
    'initial_offer': """Hi {seller_name},

I'm interested in your {item_name} listed at {asking_price}. 

Would you consider {offer_amount}? I can {payment_method} and pick up {availability}.

Thanks!""",

    'counteroffer': """Thanks for getting back to me about the {item_name}.

I understand you're looking for {seller_counter}, but my budget is tighter. 

Would {new_offer} work? That's {percent_of_asking}% of asking.""",

    'follow_up': """Hi {seller_name}, just following up on my offer for the {item_name}. 

Still interested at {offer_amount} if available!"""
}

def compose_message(template_id: str, context: dict) -> str:
    template = TEMPLATES[template_id]
    return template.format(
        **context,
        offer_amount=f"${context['offer']:,.0f}",
        percent_of_asking=round(context['offer'] / context['asking_price'] * 100)
    )
```

---

## Reseller mode: hot flip item detection

### Deal scoring algorithm with weighted factors

```python
class DealScorer:
    WEIGHTS = {
        'profit_margin': 0.30,
        'roi': 0.25,
        'sell_through_rate': 0.20,
        'competition_level': 0.10,
        'condition_factor': 0.10,
        'price_trend': 0.05
    }
    
    def score_deal(self, deal: dict) -> dict:
        net_profit = (
            deal['expected_sale_price'] 
            - deal['purchase_price'] 
            - deal['platform_fees'] 
            - deal['shipping_cost']
        )
        
        scores = {
            'profit_margin': min((net_profit / deal['expected_sale_price']) * 200, 100),
            'roi': min((net_profit / deal['purchase_price']) * 100, 100),
            'sell_through_rate': deal['sell_through_rate'] * 100,
            'competition_level': max(0, 100 - deal['competitor_count'] * 5),
            'condition_factor': {'new': 100, 'like_new': 85, 'good': 70}[deal['condition']],
            'price_trend': {'rising': 100, 'stable': 70, 'falling': 30}[deal['price_trend']]
        }
        
        total_score = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        
        rating = (
            'HOT' if total_score >= 80 else
            'GOOD' if total_score >= 60 else
            'FAIR' if total_score >= 40 else
            'PASS'
        )
        
        return {
            'score': round(total_score, 2),
            'rating': rating,
            'net_profit': round(net_profit, 2),
            'roi_pct': round((net_profit / deal['purchase_price']) * 100, 2)
        }
```

### Platform fee calculator

```python
PLATFORM_FEES = {
    'ebay': {
        'base_rate': 0.1325,  # 13.25% final value fee
        'per_order': 0.40,    # Per-order fee
        'regulatory': 0.0035  # 0.35% regulatory fee
    },
    'facebook': {
        'rate': 0.05,         # 5% or $0.40 for sales ≤$8
        'flat_threshold': 8.00
    },
    'amazon_fba': {
        'referral_rate': 0.15,  # Varies 8-45% by category
        'monthly': 39.99
    }
}

def calculate_profit(
    purchase_price: float,
    sale_price: float,
    platform: str = 'ebay',
    shipping_cost: float = 10.0,
    tax_rate: float = 0.0625
) -> dict:
    fees = PLATFORM_FEES[platform]
    
    if platform == 'ebay':
        platform_fee = sale_price * fees['base_rate'] + fees['per_order'] + sale_price * fees['regulatory']
    elif platform == 'facebook':
        platform_fee = max(0.40, sale_price * fees['rate'])
    
    purchase_tax = purchase_price * tax_rate
    total_cost = purchase_price + purchase_tax + platform_fee + shipping_cost
    net_profit = sale_price - total_cost
    
    return {
        'net_profit': round(net_profit, 2),
        'roi': round((net_profit / (purchase_price + purchase_tax)) * 100, 2),
        'break_even': round(total_cost, 2)
    }
```

### eBay sold listings lookup

```python
async def get_ebay_sold_prices(query: str, days: int = 30) -> dict:
    """Fetch recent sold listings for price comparison"""
    url = f"https://www.ebay.com/sch/i.html?_nkw={quote(query)}&LH_Sold=1&LH_Complete=1"
    
    # Use scraping API for reliability (e.g., ScrapingDog, Oxylabs)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            html = await response.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    sold_items = []
    
    for item in soup.select('.s-item'):
        price_el = item.select_one('.s-item__price')
        if price_el:
            price = float(re.sub(r'[^\d.]', '', price_el.text.split()[0]))
            sold_items.append(price)
    
    if not sold_items:
        return None
    
    return {
        'avg_price': statistics.mean(sold_items),
        'median_price': statistics.median(sold_items),
        'min_price': min(sold_items),
        'max_price': max(sold_items),
        'sample_size': len(sold_items)
    }
```

---

## Implementation phases and estimated timeline

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **1. Foundation** | Monorepo, MCP, DB | 1 week | Working browser automation scaffold |
| **2. Cost Optimization** | Model routing, caching | 1 week | 60-80% cost reduction achieved |
| **3. Lowball Mode** | Negotiation engine | 1 week | Automated offer submission working |
| **4. Reseller Mode** | Price comparison, scoring | 1 week | Deal detection and alerting live |
| **5. Dashboard** | Next.js + Shadcn | 1 week | Real-time monitoring UI complete |
| **6. Integration** | Testing, deployment | 1 week | Production-ready system |

## Conclusion: key architectural decisions

The Deal Scout architecture prioritizes **cost efficiency through intelligent model routing** rather than brute-force API calls. Haiku handles 80%+ of simple browser interactions at **$0.25/MTok** while Sonnet processes complex decisions. Prompt caching eliminates redundant context transmission, and the Batch API provides 50% discounts for background evaluations.

For Facebook Marketplace specifically, **headed Chrome with persistent profiles** proves more reliable than headless automation due to aggressive fingerprinting. The Ghost Cursor library introduces human-like mouse movements that pass behavioral analysis, while session persistence maintains login state across runs.

The **XState negotiation machine** provides deterministic state management for multi-round lowball offers, with decreasing concession rates based on academic negotiation theory. The reseller scoring algorithm combines profit margin, ROI, sell-through rate, and competition level into a single actionable score.

Finally, Kiro's spec-driven approach with **EARS notation** creates traceable requirements that map directly to implementation tasks and test cases—enabling rapid iteration while maintaining documentation accuracy.
