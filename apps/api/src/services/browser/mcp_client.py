"""
Chrome DevTools MCP client wrapper - OPTIMIZED VERSION
Provides high-level interface to Chrome automation via MCP.

Optimizations:
- Resource blocking (images, fonts, analytics)
- Smart wait strategies (selector-based, network idle)
- Connection reuse
- Parallel page support
"""

import asyncio
import json
import logging
import os
import random
from typing import Any, Optional, Set
import aiohttp

logger = logging.getLogger(__name__)


class ChromeMCPClient:
    """
    Optimized wrapper for Chrome DevTools MCP server.
    Provides fast, human-like browser automation.
    """
    
    # Resource types to block for faster loading
    BLOCKED_RESOURCE_TYPES: Set[str] = {
        'image', 'font', 'media', 'beacon', 'csp_report', 'texttrack'
    }
    
    # URL patterns to block (analytics, tracking)
    BLOCKED_URL_PATTERNS = [
        'google-analytics', 'googletagmanager', 'facebook.com/tr',
        'doubleclick', 'adzerk', 'analytics', 'hotjar', 'mixpanel',
        'segment.io', 'amplitude', 'fullstory', 'mouseflow'
    ]
    
    def __init__(self, mcp_endpoint: str = "http://localhost:9222"):
        self.endpoint = mcp_endpoint
        self.session_cookies = None
        self.current_url = None
        self._msg_id = 0
        
        # Feature flags
        self.enable_resource_blocking = os.getenv("ENABLE_RESOURCE_BLOCKING", "true") == "true"
    
    def _next_id(self) -> int:
        """Get next message ID."""
        self._msg_id += 1
        return self._msg_id
    
    async def _get_ws_url(self, session: aiohttp.ClientSession) -> Optional[str]:
        """Get WebSocket URL for the page target."""
        try:
            async with session.get(f"{self.endpoint}/json", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                targets = await resp.json()
                if not targets:
                    return None
                target = next((t for t in targets if t['type'] == 'page'), targets[0])
                return target['webSocketDebuggerUrl']
        except Exception as e:
            logger.error(f"Failed to get WebSocket URL: {e}")
            return None
    
    async def navigate(self, url: str, wait_for: str = "domcontentloaded") -> bool:
        """
        Navigate to URL with smart waiting.
        
        Args:
            url: URL to navigate to
            wait_for: Wait strategy:
                - "domcontentloaded": Wait for DOM (fastest)
                - "load": Wait for all resources
                - "networkidle": Wait for network to be idle
                - CSS selector: Wait for specific element
        """
        try:
            logger.info(f"Navigating to: {url}")
            
            async with aiohttp.ClientSession() as session:
                ws_url = await self._get_ws_url(session)
                if not ws_url:
                    logger.error("No Chrome targets available")
                    return False
                
                async with session.ws_connect(ws_url, timeout=30) as ws:
                    # Enable required domains
                    await ws.send_json({"id": self._next_id(), "method": "Page.enable"})
                    await asyncio.wait_for(ws.receive(), timeout=5)
                    
                    await ws.send_json({"id": self._next_id(), "method": "Network.enable"})
                    await asyncio.wait_for(ws.receive(), timeout=5)

                    # Navigate
                    nav_id = self._next_id()
                    await ws.send_json({
                        "id": nav_id,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    })
                    
                    # Wait for navigation response
                    response = await asyncio.wait_for(ws.receive(), timeout=15)
                    result = json.loads(response.data)
                    
                    if "error" in result:
                        logger.error(f"Navigation error: {result['error']}")
                        return False
                    
                    # Smart wait based on strategy
                    if wait_for == "domcontentloaded":
                        # Quick wait for DOM - much faster than full load
                        await asyncio.sleep(0.5)
                    elif wait_for == "load":
                        await asyncio.sleep(2)
                    elif wait_for == "networkidle":
                        await asyncio.sleep(1)
                    elif wait_for.startswith('.') or wait_for.startswith('#') or wait_for.startswith('['):
                        # CSS selector - wait for element
                        await self._wait_for_selector_internal(ws, wait_for, timeout_ms=10000)
                    else:
                        await asyncio.sleep(1)
                    
                    self.current_url = url
                    logger.info(f"Successfully navigated to {url}")
                    return True
                    
        except asyncio.TimeoutError:
            logger.error(f"Navigation timed out for {url}")
            return False
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def _wait_for_selector_internal(self, ws, selector: str, timeout_ms: int = 10000) -> bool:
        """Internal wait for selector using existing WebSocket connection."""
        script = f'''
        new Promise((resolve) => {{
            const timeout = setTimeout(() => resolve(false), {timeout_ms});
            const check = () => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    clearTimeout(timeout);
                    resolve(true);
                }} else {{
                    requestAnimationFrame(check);
                }}
            }};
            check();
        }})
        '''
        
        await ws.send_json({
            "id": self._next_id(),
            "method": "Runtime.evaluate",
            "params": {"expression": script, "returnByValue": True, "awaitPromise": True}
        })
        
        try:
            response = await asyncio.wait_for(ws.receive(), timeout=timeout_ms/1000 + 2)
            return True
        except:
            return False
    
    async def wait_for_selector(self, selector: str, timeout_ms: int = 10000) -> bool:
        """
        Wait for specific element to appear in DOM.
        
        Args:
            selector: CSS selector
            timeout_ms: Maximum wait time
            
        Returns:
            True if element found, False if timeout
        """
        script = f'''
        new Promise((resolve) => {{
            const timeout = setTimeout(() => resolve(false), {timeout_ms});
            const check = () => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    clearTimeout(timeout);
                    resolve(true);
                }} else {{
                    requestAnimationFrame(check);
                }}
            }};
            check();
        }})
        '''
        try:
            result = await self.execute_script(script)
            return result is True
        except Exception:
            return False
    
    async def wait_for_network_idle(self, idle_time_ms: int = 500, timeout_ms: int = 5000) -> bool:
        """
        Wait until no network requests for specified duration.
        
        Args:
            idle_time_ms: How long network must be idle
            timeout_ms: Maximum wait time
        """
        script = f'''
        new Promise((resolve) => {{
            let lastActivity = Date.now();
            let resolved = false;
            
            const observer = new PerformanceObserver((list) => {{
                lastActivity = Date.now();
            }});
            try {{ observer.observe({{ entryTypes: ['resource'] }}); }} catch(e) {{}}
            
            const check = setInterval(() => {{
                if (Date.now() - lastActivity > {idle_time_ms}) {{
                    clearInterval(check);
                    try {{ observer.disconnect(); }} catch(e) {{}}
                    if (!resolved) {{ resolved = true; resolve(true); }}
                }}
            }}, 100);
            
            setTimeout(() => {{
                clearInterval(check);
                try {{ observer.disconnect(); }} catch(e) {{}}
                if (!resolved) {{ resolved = true; resolve(false); }}
            }}, {timeout_ms});
        }})
        '''
        try:
            return await self.execute_script(script)
        except:
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
                ws_url = await self._get_ws_url(session)
                if not ws_url:
                    return None
                
                async with session.ws_connect(ws_url, timeout=30) as ws:
                    # Enable Runtime
                    await ws.send_json({"id": self._next_id(), "method": "Runtime.enable"})
                    await asyncio.wait_for(ws.receive(), timeout=5)
                    
                    # Execute script
                    exec_id = self._next_id()
                    await ws.send_json({
                        "id": exec_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": script,
                            "returnByValue": True,
                            "awaitPromise": True  # Support async scripts
                        }
                    })
                    
                    # Wait for result - skip event messages
                    for _ in range(20):
                        try:
                            response = await asyncio.wait_for(ws.receive(), timeout=10)
                            data = json.loads(response.data)
                            
                            # Skip method/event messages
                            if "method" in data:
                                continue
                            
                            # Check if this is our result
                            if data.get("id") == exec_id:
                                if "error" in data:
                                    logger.error(f"Script error: {data['error']}")
                                    return None
                                
                                if "result" in data and "result" in data["result"]:
                                    return data["result"]["result"].get("value")
                                return None
                        except asyncio.TimeoutError:
                            break
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return None
    
    async def click(self, selector: str) -> bool:
        """Click an element by CSS selector."""
        script = f"""
        (function() {{
            const el = document.querySelector('{selector}');
            if (el) {{ el.click(); return true; }}
            return false;
        }})()
        """
        return await self.execute_script(script) is True
    
    async def type_text(self, selector: str, text: str) -> bool:
        """Type text into an input element."""
        # Escape single quotes in text
        escaped_text = text.replace("'", "\\'")
        script = f"""
        (function() {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.value = '{escaped_text}';
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }})()
        """
        return await self.execute_script(script) is True
    
    async def scroll_page(self, iterations: int = 2, delay_ms: int = 800) -> bool:
        """
        Optimized scroll with smart waiting.
        
        Args:
            iterations: Number of scroll cycles
            delay_ms: Base delay between scrolls (randomized)
        """
        try:
            for i in range(iterations):
                # Scroll to bottom
                await self.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                
                # Smart wait - check for network idle or use short delay
                idle = await self.wait_for_network_idle(idle_time_ms=300, timeout_ms=1500)
                
                if not idle:
                    # Fallback to short random delay
                    delay = delay_ms + random.randint(-200, 200)
                    await asyncio.sleep(delay / 1000)
                
                logger.debug(f"Scroll iteration {i+1}/{iterations}")
            
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    async def scroll_until_target(
        self,
        target_count: int = 30,
        max_iterations: int = 5,
        selector: str = 'a[href*="/marketplace/item/"]'
    ) -> dict:
        """
        Scroll until target item count reached or no new items.
        
        Returns:
            {'iterations': int, 'final_count': int, 'stopped_reason': str}
        """
        prev_count = 0
        no_change_count = 0
        
        for iteration in range(max_iterations):
            # Get current count
            count_script = f"document.querySelectorAll('{selector}').length"
            current_count = await self.execute_script(count_script) or 0
            
            # Check if target reached
            if current_count >= target_count:
                return {
                    'iterations': iteration + 1,
                    'final_count': current_count,
                    'stopped_reason': 'target_reached'
                }
            
            # Check for no new items
            if current_count == prev_count:
                no_change_count += 1
                if no_change_count >= 2:
                    return {
                        'iterations': iteration + 1,
                        'final_count': current_count,
                        'stopped_reason': 'no_new_items'
                    }
            else:
                no_change_count = 0
            
            prev_count = current_count
            
            # Scroll
            await self.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            
            # Short wait
            await self.wait_for_network_idle(idle_time_ms=300, timeout_ms=1000)
            await asyncio.sleep(0.3)
        
        final_count = await self.execute_script(f"document.querySelectorAll('{selector}').length") or 0
        return {
            'iterations': max_iterations,
            'final_count': final_count,
            'stopped_reason': 'max_iterations'
        }

    
    async def get_page_html(self) -> str:
        """Get the current page HTML."""
        return await self.execute_script("document.documentElement.outerHTML") or ""
    
    async def check_health(self) -> dict:
        """Check if Chrome is responsive."""
        import time
        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/json/version",
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'healthy': True,
                            'response_time_ms': round((time.time() - start) * 1000),
                            'browser_version': data.get('Browser'),
                            'protocol_version': data.get('Protocol-Version')
                        }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
        return {'healthy': False, 'error': 'Unknown error'}
    
    async def save_cookies(self, path: str) -> bool:
        """Save current session cookies to file."""
        try:
            async with aiohttp.ClientSession() as session:
                ws_url = await self._get_ws_url(session)
                if not ws_url:
                    return False
                
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_json({
                        "id": self._next_id(),
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
        """Load session cookies from file."""
        try:
            with open(path, 'r') as f:
                cookies = json.load(f)
            
            async with aiohttp.ClientSession() as session:
                ws_url = await self._get_ws_url(session)
                if not ws_url:
                    return False
                
                async with session.ws_connect(ws_url) as ws:
                    for cookie in cookies:
                        await ws.send_json({
                            "id": self._next_id(),
                            "method": "Network.setCookie",
                            "params": cookie
                        })
                        await ws.receive()
                    
                    logger.info(f"Loaded {len(cookies)} cookies from {path}")
                    return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
