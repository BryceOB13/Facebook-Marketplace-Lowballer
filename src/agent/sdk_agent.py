"""
SDK-compatible agent for Marketplace Deal Scout.

This agent works with the Claude Agent SDK's query interface.
"""

import asyncio
import logging
import json
from typing import List, Optional
from datetime import datetime

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from src.models import Listing, DealAlert
from src.config.agent_config import AgentSettings, get_agent_settings


logger = logging.getLogger(__name__)


class SDKDealScoutAgent:
    """
    SDK-compatible Deal Scout agent.
    
    Uses Claude Agent SDK's query interface to search Facebook Marketplace.
    """
    
    def __init__(self, settings: Optional[AgentSettings] = None):
        """
        Initialize the SDK agent.
        
        Args:
            settings: Agent configuration settings
        """
        self.settings = settings or get_agent_settings()
        self.client = None
        
    async def initialize(self):
        """Initialize the Claude SDK client."""
        logger.info("Initializing Claude SDK client...")
        
        options = ClaudeAgentOptions(
            max_turns=self.settings.max_turns,
            permission_mode="bypassPermissions",
            system_prompt=self._get_system_prompt(),
            mcp_servers={
                "chrome-devtools": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "chrome-devtools-mcp@latest",
                        f"--browserUrl=http://127.0.0.1:{self.settings.chrome_debug_port}"
                    ]
                },
                "strands-agents": {
                    "command": "uvx",
                    "args": ["strands-agents-mcp-server"],
                    "env": {
                        "FASTMCP_LOG_LEVEL": "INFO"
                    }
                }
            }
        )
        
        self.client = ClaudeSDKClient(options=options)
        await self.client.connect()
        logger.info("Claude SDK client initialized and connected")
        
    async def search_deals(
        self,
        query: str,
        max_price: Optional[int] = None,
        min_price: Optional[int] = None,
        location: Optional[str] = None
    ) -> List[DealAlert]:
        """
        Search for deals on Facebook Marketplace.
        
        Args:
            query: Search keywords
            max_price: Maximum price filter
            min_price: Minimum price filter
            location: Location filter
            
        Returns:
            List of DealAlert objects
        """
        if not self.client:
            await self.initialize()
        
        # Build search URL
        search_url = self._build_url(query, min_price, max_price, location)
        
        # Create the prompt
        prompt = self._create_search_prompt(query, search_url, min_price, max_price, location)
        
        logger.info(f"Querying agent for: {query}")
        
        try:
            # Query the agent (this sends the prompt)
            await self.client.query(prompt)
            
            # Receive the response (it's an async generator)
            response_text = ""
            final_response = None
            async for message in self.client.receive_response():
                final_response = message
                logger.info(f"Received message type: {type(message)}")
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_text += block.text
            
            logger.info(f"Full response text length: {len(response_text)}")
            logger.info(f"Response text: {response_text[:500]}")
            
            # Parse the response
            listings = self._parse_response(final_response) if final_response else []
            
            # Convert to DealAlerts
            alerts = [
                DealAlert(
                    listing=listing,
                    is_new=True,
                    price_changed=False,
                    old_price=None,
                    match_reason="New listing found"
                )
                for listing in listings
            ]
            
            return alerts
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
    
    def _build_url(
        self,
        query: str,
        min_price: Optional[int],
        max_price: Optional[int],
        location: Optional[str]
    ) -> str:
        """Build Facebook Marketplace search URL."""
        url = f"https://www.facebook.com/marketplace/search?query={query}"
        
        if min_price is not None:
            url += f"&minPrice={min_price}"
        if max_price is not None:
            url += f"&maxPrice={max_price}"
        if location:
            url += f"&location={location}"
            
        return url
    
    def _create_search_prompt(
        self,
        query: str,
        search_url: str,
        min_price: Optional[int],
        max_price: Optional[int],
        location: Optional[str]
    ) -> str:
        """Create the search prompt for the agent."""
        price_range = ""
        if min_price is not None or max_price is not None:
            price_range = f" priced between ${min_price or 0} and ${max_price or '∞'}"
        
        location_str = f" in {location}" if location else ""
        
        return f"""Please search Facebook Marketplace for {query}{price_range}{location_str}.

URL to navigate to: {search_url}

Steps:
1. Navigate to the URL above
2. Wait for the page to fully load (wait for 'load' event)
3. Scroll down 2-3 times to load more listings (wait 2-3 seconds between scrolls)
4. Find all listing links on the page (look for links with href containing "/marketplace/item/")
5. Click on the FIRST 3-5 listings one by one to get detailed information
6. For each listing you click:
   - Wait for the detail page to load
   - Extract the full details (title, price, description, seller info, location)
   - Go back to the search results
   - Click the next listing

For each listing, extract:
- id: Extract from the URL (format: /marketplace/item/ID/)
- title: The listing title text
- price: The price (e.g., "$500", "$1,200")
- description: Full item description (from detail page)
- location: The location text
- seller: Seller name (if available)
- image_url: The main image source URL
- url: The full marketplace URL

Return the results as a JSON array of listings. Format:
```json
[
  {{
    "id": "123456789",
    "title": "Example Laptop",
    "price": "$500",
    "description": "Full description from detail page...",
    "location": "San Francisco, CA",
    "seller": "John Doe",
    "image_url": "https://...",
    "url": "https://www.facebook.com/marketplace/item/123456789/"
  }}
]
```

IMPORTANT: Click on each listing to get the full details. Don't just extract from the search results page."""
    
    def _parse_response(self, response) -> List[Listing]:
        """Parse the agent response into Listing objects."""
        listings = []
        
        try:
            # Extract text from response
            text = ""
            if hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        text += block.text + "\n"
            else:
                text = str(response)
            
            # Try to find JSON in the response
            import re
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                
                for item in data:
                    listing = Listing(
                        id=item.get('id', ''),
                        title=item.get('title'),
                        price=item.get('price'),
                        location=item.get('location'),
                        image_url=item.get('image_url'),
                        url=item.get('url', '')
                    )
                    listings.append(listing)
            else:
                logger.warning("No JSON found in response, trying to parse text")
                # Fallback: try to parse as plain JSON
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        for item in data:
                            listing = Listing(
                                id=item.get('id', ''),
                                title=item.get('title'),
                                price=item.get('price'),
                                location=item.get('location'),
                                image_url=item.get('image_url'),
                                url=item.get('url', '')
                            )
                            listings.append(listing)
                except json.JSONDecodeError:
                    logger.error("Could not parse response as JSON")
                    
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
        
        return listings
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are a Marketplace Deal Scout agent that searches Facebook Marketplace for deals.

Your workflow:
1. Navigate to marketplace search URLs using chrome-devtools MCP tools
2. Wait for pages to load completely
3. Scroll to load additional listings (use evaluate_script to scroll)
4. CLICK on individual listings to view full details
5. Extract detailed information from each listing page
6. Navigate back to search results and click the next listing
7. Return results as structured JSON

Key behaviors:
- Always wait for page load events before extracting data
- Use randomized delays between actions (2-3 seconds)
- CLICK on listings to get full details (title, price, description, seller)
- Use JavaScript to find clickable listing links
- Navigate back after viewing each listing
- Extract complete listing information including descriptions
- Return results in the requested JSON format

When finding and clicking listings:
- Use evaluate_script to find all links with href containing "/marketplace/item/"
- Click on each link using the chrome-devtools click or navigation tools
- Wait for the detail page to load
- Extract all available information (title, price, description, location, seller)
- Use browser back button or navigate back to search results
- Repeat for the next listing

Always return results as a JSON array in a code block with complete details from the listing pages."""
