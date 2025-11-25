"""
Chrome browser navigator using Chrome DevTools Protocol.

Manages browser navigation, page load synchronization, and modal dismissal
through MCP tool invocations with integrated error handling and retry logic.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Dict
from src.error_handling.error_handler import ErrorHandler


# Configure logging
logger = logging.getLogger(__name__)


class ChromeNavigator:
    """
    Manages browser navigation and page load synchronization via Chrome DevTools MCP.
    
    Integrates with ErrorHandler for retry logic on navigation failures.
    Requires an agent instance to access MCP tools.
    
    Attributes:
        agent: Agent instance with access to MCP tools
        error_handler: ErrorHandler for retry logic
        mcp_tool_prefix: Prefix for MCP tool names (default: "mcp__chrome-devtools__")
        debug_port: Chrome DevTools Protocol debug port
    """
    
    def __init__(
        self,
        agent: Any,
        debug_port: int = 9222,
        mcp_tool_prefix: str = "mcp__chrome-devtools__",
        error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize Chrome navigator with MCP tool access.
        
        Args:
            agent: Agent instance with MCP tool access
            debug_port: Chrome DevTools Protocol debug port (default: 9222)
            mcp_tool_prefix: Prefix for MCP tool names (default: "mcp__chrome-devtools__")
            error_handler: ErrorHandler instance for retry logic (optional)
        """
        self.agent = agent
        self.debug_port = debug_port
        self.mcp_tool_prefix = mcp_tool_prefix
        self.error_handler = error_handler or ErrorHandler()
        
        logger.info(
            f"ChromeNavigator initialized with debug_port={debug_port}, "
            f"mcp_tool_prefix={mcp_tool_prefix}"
        )
    
    async def navigate_to_url(
        self,
        url: str,
        timeout_ms: int = 30000
    ) -> bool:
        """
        Navigate to a URL and wait for page load completion.
        
        Uses the mcp__chrome-devtools__navigate_page tool to navigate and
        integrates with ErrorHandler for retry logic on failures.
        
        Args:
            url: The URL to navigate to
            timeout_ms: Timeout in milliseconds for navigation (default: 30000)
            
        Returns:
            True if navigation succeeded, False otherwise
            
        Raises:
            Exception: If navigation fails after all retry attempts
        """
        logger.info(f"Navigating to URL: {url} with timeout {timeout_ms}ms")
        
        async def _navigate():
            """Internal navigation operation."""
            # Get the navigate_page tool from agent
            tool_name = f"{self.mcp_tool_prefix}navigate_page"
            
            # Call the MCP tool
            result = await self.agent.call_tool(
                tool_name,
                {
                    "url": url,
                    "timeout_ms": timeout_ms
                }
            )
            
            # Check if navigation was successful
            if result and result.get("success"):
                logger.info(f"Successfully navigated to {url}")
                return True
            else:
                error_msg = result.get("error", "Unknown navigation error") if result else "No response"
                raise Exception(f"Navigation failed: {error_msg}")
        
        try:
            # Use retry logic for navigation
            return await self.error_handler.retry_with_backoff(_navigate)
        except Exception as e:
            logger.error(f"Navigation to {url} failed after retries: {str(e)}")
            raise
    
    async def wait_for_page_load(
        self,
        event: str = "load",
        timeout_ms: int = 15000
    ) -> bool:
        """
        Wait for a specific page event to occur.
        
        Uses the mcp__chrome-devtools__wait_for tool to wait for page events
        like "load", "networkidle", etc.
        
        Args:
            event: The event to wait for (default: "load")
            timeout_ms: Timeout in milliseconds (default: 15000)
            
        Returns:
            True if event occurred within timeout, False otherwise
            
        Raises:
            Exception: If wait operation fails after all retry attempts
        """
        logger.info(f"Waiting for page event: {event} with timeout {timeout_ms}ms")
        
        async def _wait():
            """Internal wait operation."""
            # Get the wait_for tool from agent
            tool_name = f"{self.mcp_tool_prefix}wait_for"
            
            # Call the MCP tool
            result = await self.agent.call_tool(
                tool_name,
                {
                    "event": event,
                    "timeout_ms": timeout_ms
                }
            )
            
            # Check if wait was successful
            if result and result.get("success"):
                logger.info(f"Page event '{event}' occurred")
                return True
            else:
                error_msg = result.get("error", "Unknown wait error") if result else "No response"
                raise Exception(f"Wait for event failed: {error_msg}")
        
        try:
            # Use retry logic for wait operation
            return await self.error_handler.retry_with_backoff(_wait)
        except Exception as e:
            logger.error(f"Wait for event '{event}' failed after retries: {str(e)}")
            raise
    
    async def dismiss_login_modal(self) -> bool:
        """
        Dismiss Facebook login modal if present.
        
        Executes JavaScript to press Escape key and click close button
        to dismiss login modals that may appear during navigation.
        
        Returns:
            True if modal was dismissed or not present, False if dismissal failed
        """
        logger.info("Attempting to dismiss login modal")
        
        # JavaScript to dismiss login modal
        dismiss_script = """
        async () => {
            try {
                // Try pressing Escape key
                const escapeEvent = new KeyboardEvent('keydown', {
                    key: 'Escape',
                    code: 'Escape',
                    keyCode: 27,
                    which: 27,
                    bubbles: true,
                    cancelable: true
                });
                document.dispatchEvent(escapeEvent);
                
                // Wait a moment for modal to respond to Escape
                await new Promise(r => setTimeout(r, 500));
                
                // Try clicking close button (common selectors for Facebook modals)
                const closeButtons = document.querySelectorAll(
                    '[aria-label="Close"], [data-testid="modal_close_button"], .x1iyjqo2'
                );
                
                for (const btn of closeButtons) {
                    if (btn && btn.offsetParent !== null) {  // Check if visible
                        btn.click();
                        await new Promise(r => setTimeout(r, 300));
                        break;
                    }
                }
                
                return {
                    success: true,
                    message: "Login modal dismissed or not present"
                };
            } catch (error) {
                return {
                    success: false,
                    error: error.message
                };
            }
        }
        """
        
        try:
            # Get the evaluate_script tool from agent
            tool_name = f"{self.mcp_tool_prefix}evaluate_script"
            
            # Call the MCP tool
            result = await self.agent.call_tool(
                tool_name,
                {
                    "script": dismiss_script
                }
            )
            
            # Check if script executed successfully
            if result and result.get("success"):
                logger.info("Login modal dismissed successfully")
                return True
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                logger.warning(f"Modal dismissal script failed: {error_msg}")
                # Don't raise - modal might not be present, which is fine
                return True
                
        except Exception as e:
            logger.warning(f"Error dismissing login modal: {str(e)}")
            # Don't raise - modal might not be present, which is fine
            return True
    
    async def navigate_and_wait(
        self,
        url: str,
        event: str = "load",
        navigation_timeout_ms: int = 30000,
        wait_timeout_ms: int = 15000
    ) -> bool:
        """
        Navigate to URL and wait for page load in a single operation.
        
        Combines navigation and page load waiting with error handling.
        
        Args:
            url: The URL to navigate to
            event: The event to wait for (default: "load")
            navigation_timeout_ms: Timeout for navigation (default: 30000)
            wait_timeout_ms: Timeout for wait operation (default: 15000)
            
        Returns:
            True if both navigation and wait succeeded
            
        Raises:
            Exception: If either operation fails after retries
        """
        logger.info(f"Starting navigate_and_wait for {url}")
        
        try:
            # First navigate to the URL
            await self.navigate_to_url(url, timeout_ms=navigation_timeout_ms)
            
            # Then wait for page load
            await self.wait_for_page_load(event=event, timeout_ms=wait_timeout_ms)
            
            # Try to dismiss any login modals
            await self.dismiss_login_modal()
            
            logger.info(f"Successfully navigated and loaded {url}")
            return True
            
        except Exception as e:
            logger.error(f"navigate_and_wait failed for {url}: {str(e)}")
            raise
