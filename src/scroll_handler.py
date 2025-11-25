"""
Scroll handler for loading additional marketplace listings.

This module provides the ScrollHandler class that executes infinite scroll
operations to load more listings on Facebook Marketplace pages.
"""

import random
from typing import Callable, Awaitable


class ScrollHandler:
    """Executes infinite scroll to load additional listings.
    
    Performs configurable scroll iterations with randomized delays to simulate
    human-like browsing behavior and allow content to load between scrolls.
    """
    
    def __init__(
        self,
        scroll_iterations: int = 3,
        min_delay_ms: int = 2000,
        max_delay_ms: int = 4500
    ):
        """Initialize scroll configuration.
        
        Args:
            scroll_iterations: Number of scroll-and-wait cycles to execute
            min_delay_ms: Minimum delay in milliseconds after each scroll
            max_delay_ms: Maximum delay in milliseconds after each scroll
        """
        self.scroll_iterations = scroll_iterations
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
    
    async def scroll_and_load(
        self,
        execute_script_fn: Callable[[str], Awaitable[str]]
    ) -> bool:
        """Execute scroll iterations with randomized delays.
        
        Scrolls to the bottom of the page multiple times with delays between
        each scroll to allow dynamic content to load.
        
        Args:
            execute_script_fn: Async function that executes JavaScript in browser context
            
        Returns:
            True if scrolling completed successfully, False otherwise
            
        Raises:
            RuntimeError: If script execution fails
        """
        script = self._generate_scroll_script()
        
        try:
            result = await execute_script_fn(script)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to execute scroll script: {e}")
    
    def _generate_scroll_script(self) -> str:
        """Generate JavaScript for scrolling with delays.
        
        Creates a JavaScript function that scrolls to document.body.scrollHeight
        multiple times with randomized delays between scrolls.
        
        Returns:
            JavaScript code as a string that performs scroll operations
        """
        # Generate the scroll script with configured parameters
        script = f"""
async () => {{
  const scrollAndWait = async () => {{
    // Scroll to the bottom of the page
    window.scrollTo(0, document.body.scrollHeight);
    
    // Wait with randomized delay between {self.min_delay_ms}ms and {self.max_delay_ms}ms
    const delay = {self.min_delay_ms} + Math.random() * ({self.max_delay_ms} - {self.min_delay_ms});
    await new Promise(r => setTimeout(r, delay));
  }};
  
  // Execute scroll iterations
  for (let i = 0; i < {self.scroll_iterations}; i++) {{
    await scrollAndWait();
  }}
  
  return 'Scrolling complete';
}}
"""
        return script
    
    def get_random_delay(self) -> int:
        """Generate a random delay value within configured bounds.
        
        Returns:
            Random delay in milliseconds between min_delay_ms and max_delay_ms
        """
        return random.randint(self.min_delay_ms, self.max_delay_ms)
