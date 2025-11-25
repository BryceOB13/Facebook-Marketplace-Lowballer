"""
Agent orchestrator for Marketplace Deal Scout.

Coordinates the full workflow of searching, extracting, filtering, and tracking
marketplace deals using Claude Agent SDK with multiple MCP servers.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from src.models import Listing, SearchCriteria, DealAlert
from src.url_builder import MarketplaceURLBuilder
from src.browser_automation.chrome_navigator import ChromeNavigator
from src.scroll_handler import ScrollHandler
from src.extraction_engine import ListingExtractor
from src.filtering.listing_filter import ListingFilter
from src.memory.memory_manager import DealMemoryManager
from src.session.session_manager import DealScoutSessionManager
from src.rate_limiting.rate_limiter import RateLimiter
from src.error_handling.error_handler import ErrorHandler
from src.config.agent_config import AgentSettings, get_agent_settings


# Configure logging
logger = logging.getLogger(__name__)


class DealScoutAgent:
    """
    Main agent orchestrator for Marketplace Deal Scout.
    
    Coordinates the full workflow of searching, extracting, filtering, and tracking
    marketplace deals. Integrates with Chrome DevTools MCP for browser automation
    and Strands Agents MCP for memory persistence.
    
    Attributes:
        agent: Claude Agent SDK client instance
        settings: Agent configuration settings
        url_builder: URL construction component
        navigator: Chrome browser navigation component
        scroll_handler: Infinite scroll component
        extractor: Listing extraction component
        filter: Result filtering component
        memory_manager: Persistent memory component
        session_manager: Session persistence component
        rate_limiter: Rate limiting component
        error_handler: Error handling and retry component
    """
    
    def __init__(
        self,
        agent: Any,
        settings: Optional[AgentSettings] = None,
        mem0_tool: Optional[Callable] = None
    ):
        """
        Initialize the Deal Scout agent.
        
        Args:
            agent: Claude Agent SDK client instance with MCP tool access
            settings: Agent configuration settings (uses defaults if not provided)
            mem0_tool: Callable mem0_memory MCP tool for memory operations
        """
        self.agent = agent
        self.settings = settings or get_agent_settings()
        self.mem0_tool = mem0_tool
        
        # Initialize components
        self.url_builder = MarketplaceURLBuilder()
        
        self.error_handler = ErrorHandler(
            max_retries=self.settings.retry_config.max_retries,
            timeout_multiplier=self.settings.retry_config.timeout_multiplier
        )
        
        self.navigator = ChromeNavigator(
            agent=agent,
            debug_port=self.settings.chrome_debug_port,
            error_handler=self.error_handler
        )
        
        self.scroll_handler = ScrollHandler(
            scroll_iterations=self.settings.scroll_config.iterations,
            min_delay_ms=self.settings.scroll_config.min_delay_ms,
            max_delay_ms=self.settings.scroll_config.max_delay_ms
        )
        
        self.extractor = ListingExtractor()
        self.filter = ListingFilter()
        
        self.memory_manager = DealMemoryManager(
            user_id=self.settings.memory_config.user_id,
            mem0_tool=mem0_tool
        )
        
        self.session_manager = DealScoutSessionManager(
            session_id=self.settings.session_id,
            storage_type=self.settings.memory_config.storage_type,
            base_dir=self.settings.memory_config.base_dir
        )
        
        self.rate_limiter = RateLimiter(
            min_delay_seconds=self.settings.rate_limiting.min_delay_seconds,
            max_delay_seconds=self.settings.rate_limiting.max_delay_seconds,
            max_pages_per_hour=self.settings.rate_limiting.max_pages_per_hour
        )
        
        logger.info("DealScoutAgent initialized successfully")
    
    async def search_deals(
        self,
        query: str,
        max_price: Optional[int] = None,
        min_price: Optional[int] = None,
        location: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[DealAlert]:
        """
        Execute the complete deal search workflow.
        
        Orchestrates the full pipeline: URL construction, navigation, scrolling,
        extraction, filtering, memory comparison, and result presentation.
        
        Args:
            query: Search keywords
            max_price: Maximum price filter (optional)
            min_price: Minimum price filter (optional)
            location: Location filter (optional)
            category: Category for memory storage (optional)
            
        Returns:
            List of DealAlert objects representing found deals
            
        Raises:
            Exception: If critical operations fail after retry attempts
        """
        logger.info(
            f"Starting deal search: query='{query}', "
            f"price_range=[{min_price}, {max_price}], location='{location}'"
        )
        
        try:
            # Load session state
            session_state = self.session_manager.load_session()
            logger.info(f"Loaded session: {session_state.get('session_id')}")
            
            # Check rate limiting
            if not self.rate_limiter.check_hourly_limit():
                raise Exception(
                    "Hourly request limit reached. Please wait before making more requests."
                )
            
            # Build search URL
            search_url = self.url_builder.build_search_url(
                query=query,
                min_price=min_price,
                max_price=max_price,
                location=location
            )
            logger.info(f"Built search URL: {search_url}")
            
            # Navigate to marketplace
            logger.info("Navigating to marketplace search page...")
            await self.navigator.navigate_and_wait(
                url=search_url,
                event="load",
                navigation_timeout_ms=self.settings.retry_config.initial_timeout_ms,
                wait_timeout_ms=15000
            )
            
            # Record the request for rate limiting
            self.rate_limiter.record_request()
            
            # Wait between actions (rate limiting)
            await self.rate_limiter.wait_between_actions()
            
            # Scroll to load more listings
            logger.info("Scrolling to load additional listings...")
            await self.scroll_handler.scroll_and_load(
                execute_script_fn=self._execute_script
            )
            
            # Wait between actions
            await self.rate_limiter.wait_between_actions()
            
            # Extract listings from page
            logger.info("Extracting listings from page...")
            listings = await self.extractor.extract_listings(
                execute_script_fn=self._execute_script
            )
            logger.info(f"Extracted {len(listings)} listings")
            
            # Filter by price
            if min_price is not None or max_price is not None:
                logger.info(f"Filtering by price range: [{min_price}, {max_price}]")
                listings = self.filter.filter_by_price(
                    listings,
                    min_price=min_price,
                    max_price=max_price
                )
                logger.info(f"After price filter: {len(listings)} listings")
            
            # Filter by location if provided
            if location:
                logger.info(f"Filtering by location: {location}")
                listings = self.filter.filter_by_location(listings, location)
                logger.info(f"After location filter: {len(listings)} listings")
            
            # Compare against memory and create alerts
            logger.info("Comparing against memory and creating alerts...")
            alerts = await self._create_deal_alerts(
                listings=listings,
                category=category or query
            )
            logger.info(f"Created {len(alerts)} deal alerts")
            
            # Update session state
            session_state = self.session_manager.update_session_timestamp(session_state)
            session_state = self.session_manager.add_search_to_history(
                session_state,
                query=query,
                filters={
                    "min_price": min_price,
                    "max_price": max_price,
                    "location": location
                }
            )
            
            # Save session state
            self.session_manager.save_session(session_state)
            logger.info("Session state saved")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Deal search failed: {str(e)}")
            raise
    
    async def _create_deal_alerts(
        self,
        listings: List[Listing],
        category: str
    ) -> List[DealAlert]:
        """
        Create DealAlert objects by comparing listings against memory.
        
        For each listing, checks if it's new or has a price change, then
        stores it in memory for future comparisons.
        
        Args:
            listings: List of extracted listings
            category: Category for memory storage
            
        Returns:
            List of DealAlert objects
        """
        alerts = []
        
        for listing in listings:
            try:
                # Check if listing is new
                is_new = await self.memory_manager.check_if_new(listing.id)
                
                # Check for price changes
                price_changed = False
                old_price = None
                
                if not is_new:
                    price_change = await self.memory_manager.detect_price_change(
                        listing.id,
                        listing.price or ""
                    )
                    if price_change:
                        old_price, new_price = price_change
                        price_changed = True
                
                # Create alert
                match_reason = ""
                if is_new:
                    match_reason = "New listing found"
                elif price_changed:
                    match_reason = f"Price changed from {old_price} to {listing.price}"
                
                alert = DealAlert(
                    listing=listing,
                    is_new=is_new,
                    price_changed=price_changed,
                    old_price=old_price,
                    match_reason=match_reason
                )
                
                alerts.append(alert)
                
                # Store listing in memory for future comparisons
                await self.memory_manager.store_listing(listing, category)
                
            except Exception as e:
                logger.warning(f"Error processing listing {listing.id}: {str(e)}")
                # Continue with next listing
                continue
        
        return alerts
    
    async def _execute_script(self, script: str) -> str:
        """
        Execute JavaScript in the browser context.
        
        Wrapper around the Chrome DevTools MCP tool for script execution.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result from script execution
            
        Raises:
            Exception: If script execution fails
        """
        try:
            tool_name = "mcp__chrome-devtools__evaluate_script"
            result = await self.agent.call_tool(
                tool_name,
                {"script": script}
            )
            
            if result and result.get("success"):
                return result.get("result", "")
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                raise Exception(f"Script execution failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Script execution error: {str(e)}")
            raise
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the agent.
        
        Returns:
            System prompt string with workflow instructions
        """
        return """You are a Marketplace Deal Scout agent that searches Facebook Marketplace for deals.

Your workflow:
1. Navigate to marketplace search URLs
2. Wait for pages to load completely
3. Scroll to load additional listings
4. Extract listing data using JavaScript
5. Filter results by price and location
6. Compare against memory to find new deals and price changes
7. Present results to the user

Key behaviors:
- Always wait between actions to avoid detection (3-7 seconds)
- Use randomized delays for human-like behavior
- Respect rate limits (max 10 pages per hour)
- Handle errors gracefully with retry logic
- Store deals in memory for cross-session tracking

When extracting listings, use stable selectors:
- URL patterns: /marketplace/item/{ID}/
- ARIA attributes for accessibility
- Avoid obfuscated CSS classes

Always provide complete listing information:
- Listing ID (required)
- Title (required if price not available)
- Price (required if title not available)
- Location (when available)
- Image URL (when available)
- Full marketplace URL

Report new deals and price changes clearly to help users find opportunities."""
    
    def get_allowed_tools(self) -> List[str]:
        """
        Get the list of allowed MCP tools for the agent.
        
        Returns:
            List of tool names that the agent can invoke
        """
        return [
            # Chrome DevTools tools
            "mcp__chrome-devtools__navigate_page",
            "mcp__chrome-devtools__wait_for",
            "mcp__chrome-devtools__evaluate_script",
            "mcp__chrome-devtools__capture_screenshot",
            
            # Strands Agents tools
            "mcp__strands-agents__mem0_memory",
            "mcp__strands-agents__search_memory",
            "mcp__strands-agents__store_memory",
        ]

