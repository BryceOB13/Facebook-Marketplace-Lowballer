"""
Chrome DevTools MCP client wrapper.
Provides high-level interface to Chrome automation via MCP.
"""

import asyncio
import json
import logging
import random
from typing import Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


class ChromeMCPClient:
    """
    Wrapper for Chrome DevTools MCP server.
    Provides human-like browser automation.
    """
    
    def __init__(self, mcp_endpoint: str = "http://localhost:9222"):
        self.endpoint = mcp_endpoint
        self.session_cookies = None
        self.current_url = None
    
    async def navigate(self, url: str, wait_for: str = "load") -> bool:
        """
        Navigate to a URL and wait for page load.
        
        Args:
            url: URL to navigate to
            wait_for: Event to wait for ("load", "domcontentloaded", "networkidle")
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Navigating to: {url}")
            
            # Use Chrome DevTools Protocol via MCP
            # For MVP, we'll use direct CDP commands
            async with aiohttp.ClientSession() as session:
                # Get list of targets
                async with session.get(f"{self.endpoint}/json") as resp:
                    targets = await resp.json()
                    if not targets:
                        logger.error("No Chrome targets available")
                        return False
                    
                    # Use first page target
                    target = next((t for t in targets if t['type'] == 'page'), targets[0])
                    ws_url = target['webSocketDebuggerUrl']
                
                # Connect to WebSocket and send navigation command
                async with session.ws_connect(ws_url) as ws:
                    # Enable Page domain
                    await ws.send_json({
                        "id": 1,
                        "method": "Page.enable"
                    })
                    await ws.receive()
                    
                    # Navigate
                    await ws.send_json({
                        "id": 2,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    })
                    
                    # Wait for response
                    response = await ws.receive()
                    result = json.loads(response.data)
                    
                    if "error" in result:
                        logger.error(f"Navigation error: {result['error']}")
                        return False
                    
                    # Wait for load event
                    await asyncio.sleep(2)  # Simple wait for MVP
                    
                    self.current_url = url
                    logger.info(f"Successfully navigated to {url}")
                    return True
                    
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript in the browser context.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result from script execution
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get WebSocket URL
                async with session.get(f"{self.endpoint}/json") as resp:
                    targets = await resp.json()
                    target = next((t for t in targets if t['type'] == 'page'), targets[0])
                    ws_url = target['webSocketDebuggerUrl']
                
                async with session.ws_connect(ws_url) as ws:
                    # Enable Runtime and Console
                    await ws.send_json({
                        "id": 1,
                        "method": "Runtime.enable"
                    })
                    await ws.receive()
                    
                    await ws.send_json({
                        "id": 2,
                        "method": "Console.enable"
                    })
                    await ws.receive()
                    
                    # Execute script
                    await ws.send_json({
                        "id": 3,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": script,
                            "returnByValue": True,
                            "awaitPromise": False
                        }
                    })
                    
                    # Wait for result - skip context/console messages
                    result = None
                    max_messages = 20  # Read up to 20 messages
                    
                    for i in range(max_messages):
                        try:
                            response = await asyncio.wait_for(ws.receive(), timeout=3.0)
                            data = json.loads(response.data)
                            
                            # Skip method messages (context, console, etc)
                            if "method" in data:
                                method = data.get("method")
                                if method == "Runtime.consoleAPICalled":
                                    # Log console output
                                    args = data.get("params", {}).get("args", [])
                                    if args:
                                        logger.debug(f"Console: {args[0].get('value')}")
                                continue
                            
                            # Check if this is our result
                            if data.get("id") == 3:
                                result = data
                                break
                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout waiting for message {i+1}/{max_messages}")
                            break
                        except Exception as e:
                            logger.error(f"Error receiving message: {e}")
                            break
                    
                    if not result:
                        logger.error("No result received from script execution")
                        return None
                    
                    if "error" in result:
                        logger.error(f"Script execution error: {result['error']}")
                        return None
                    
                    if "result" in result and "result" in result["result"]:
                        value = result["result"]["result"].get("value")
                        return value
                    
                    logger.warning(f"Unexpected result format: {result}")
                    return None
                    
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return None
    
    async def click(self, selector: str) -> bool:
        """
        Click an element by CSS selector.
        
        Args:
            selector: CSS selector
            
        Returns:
            True if successful
        """
        script = f"""
        (function() {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.click();
                return true;
            }}
            return false;
        }})()
        """
        result = await self.execute_script(script)
        return result is True
    
    async def type_text(self, selector: str, text: str) -> bool:
        """
        Type text into an input element.
        
        Args:
            selector: CSS selector
            text: Text to type
            
        Returns:
            True if successful
        """
        script = f"""
        (function() {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.value = '{text}';
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }})()
        """
        result = await self.execute_script(script)
        return result is True
    
    async def scroll_page(self, iterations: int = 3, delay_ms: int = 2000) -> bool:
        """
        Scroll page to load more content.
        
        Args:
            iterations: Number of scroll cycles
            delay_ms: Delay between scrolls (milliseconds)
            
        Returns:
            True if successful
        """
        try:
            for i in range(iterations):
                # Scroll to bottom
                await self.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                
                # Random human-like delay
                delay = delay_ms + random.randint(-500, 500)
                await asyncio.sleep(delay / 1000)
                
                logger.info(f"Scroll iteration {i+1}/{iterations}")
            
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    async def get_page_html(self) -> str:
        """
        Get the current page HTML.
        
        Returns:
            Page HTML as string
        """
        script = "document.documentElement.outerHTML"
        return await self.execute_script(script) or ""
    
    async def save_cookies(self, path: str) -> bool:
        """
        Save current session cookies to file.
        
        Args:
            path: File path to save cookies
            
        Returns:
            True if successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.endpoint}/json") as resp:
                    targets = await resp.json()
                    target = next((t for t in targets if t['type'] == 'page'), targets[0])
                    ws_url = target['webSocketDebuggerUrl']
                
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_json({
                        "id": 1,
                        "method": "Network.getAllCookies"
                    })
                    
                    response = await ws.receive()
                    result = json.loads(response.data)
                    
                    if "result" in result and "cookies" in result["result"]:
                        cookies = result["result"]["cookies"]
                        with open(path, 'w') as f:
                            json.dump(cookies, f)
                        logger.info(f"Saved {len(cookies)} cookies to {path}")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    async def load_cookies(self, path: str) -> bool:
        """
        Load session cookies from file.
        
        Args:
            path: File path to load cookies from
            
        Returns:
            True if successful
        """
        try:
            with open(path, 'r') as f:
                cookies = json.load(f)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.endpoint}/json") as resp:
                    targets = await resp.json()
                    target = next((t for t in targets if t['type'] == 'page'), targets[0])
                    ws_url = target['webSocketDebuggerUrl']
                
                async with session.ws_connect(ws_url) as ws:
                    for cookie in cookies:
                        await ws.send_json({
                            "id": 1,
                            "method": "Network.setCookie",
                            "params": cookie
                        })
                        await ws.receive()
                    
                    logger.info(f"Loaded {len(cookies)} cookies from {path}")
                    return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
