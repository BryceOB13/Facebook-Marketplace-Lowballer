"""
Error handler with retry logic for marketplace deal scout.

Implements exponential backoff, timeout escalation, and error recovery strategies.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from datetime import datetime


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior with exponential backoff.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        initial_timeout_ms: Initial timeout value in milliseconds
        timeout_multiplier: Multiplier for timeout escalation on each retry
    """
    max_retries: int = 3
    initial_timeout_ms: int = 30000
    timeout_multiplier: float = 1.5
    
    def get_timeout(self, attempt: int) -> int:
        """
        Calculate timeout for a specific retry attempt.
        
        Timeout escalates exponentially with each attempt using the formula:
        timeout = initial_timeout_ms * (timeout_multiplier ^ attempt)
        
        Args:
            attempt: The retry attempt number (0-indexed)
            
        Returns:
            Timeout value in milliseconds for the given attempt
        """
        return int(self.initial_timeout_ms * (self.timeout_multiplier ** attempt))
    
    def get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate backoff delay before retry attempt.
        
        Uses exponential backoff with base of 2 seconds:
        delay = 2.0 * (2 ^ attempt)
        
        Args:
            attempt: The retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds before the retry attempt
        """
        return 2.0 * (2 ** attempt)


class ErrorHandler:
    """
    Error handler with retry logic and diagnostic capabilities.
    
    Provides exponential backoff, timeout escalation, and error recovery
    strategies for browser automation operations.
    
    Attributes:
        config: Retry configuration
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        timeout_multiplier: float = 1.5
    ):
        """
        Initialize error handler with retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            timeout_multiplier: Multiplier for timeout escalation (default: 1.5)
        """
        self.config = RetryConfig(
            max_retries=max_retries,
            timeout_multiplier=timeout_multiplier
        )
    
    async def retry_with_backoff(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with exponential backoff retry logic.
        
        Attempts the operation up to max_retries times, with escalating timeouts
        and exponential backoff delays between attempts. Logs all attempts and
        errors with diagnostic context.
        
        Args:
            operation: Async callable to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result from successful operation execution
            
        Raises:
            Exception: The last exception encountered if all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Log attempt
                logger.info(
                    f"Attempt {attempt + 1}/{self.config.max_retries} for operation {operation.__name__}"
                )
                
                # Calculate timeout for this attempt
                timeout = self.config.get_timeout(attempt)
                
                # Update timeout in kwargs if operation accepts it
                if 'timeout_ms' in kwargs:
                    kwargs['timeout_ms'] = timeout
                
                # Execute operation
                result = await operation(*args, **kwargs)
                
                # Success - log and return
                logger.info(f"Operation {operation.__name__} succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Log error with context
                self._log_error(
                    operation_name=operation.__name__,
                    attempt=attempt + 1,
                    max_attempts=self.config.max_retries,
                    error=e,
                    args=args,
                    kwargs=kwargs
                )
                
                # If this was the last attempt, don't wait
                if attempt == self.config.max_retries - 1:
                    logger.error(
                        f"Operation {operation.__name__} failed after {self.config.max_retries} attempts. "
                        f"Final error: {str(e)}"
                    )
                    break
                
                # Calculate and apply backoff delay
                backoff_delay = self.config.get_backoff_delay(attempt)
                logger.info(f"Waiting {backoff_delay:.1f}s before retry...")
                await asyncio.sleep(backoff_delay)
        
        # All retries exhausted - raise the last exception
        raise last_exception
    
    async def handle_chrome_timeout(
        self,
        error: Exception
    ) -> Dict[str, str]:
        """
        Provide recovery suggestions for Chrome timeout errors.
        
        Analyzes Chrome-related errors and provides actionable recovery
        suggestions for common timeout scenarios.
        
        Args:
            error: The Chrome timeout exception
            
        Returns:
            Dictionary with error analysis and recovery suggestions
        """
        error_str = str(error).lower()
        
        suggestions = {
            'error_type': 'Chrome Timeout',
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'recovery_suggestions': []
        }
        
        # Analyze error and provide specific suggestions
        if 'connection' in error_str or 'connect' in error_str:
            suggestions['recovery_suggestions'].extend([
                'Verify Chrome is running with remote debugging enabled',
                'Check that the debugging port (9222) is correct and accessible',
                'Ensure no firewall is blocking the connection',
                'Try restarting Chrome with the --remote-debugging-port flag'
            ])
        elif 'timeout' in error_str or 'timed out' in error_str:
            suggestions['recovery_suggestions'].extend([
                'Increase the timeout value for the operation',
                'Check your internet connection speed',
                'Verify the target page is loading correctly in the browser',
                'Try reducing the number of concurrent operations'
            ])
        elif 'navigation' in error_str:
            suggestions['recovery_suggestions'].extend([
                'Verify the URL is correct and accessible',
                'Check if the page requires authentication',
                'Try navigating to the page manually in Chrome first',
                'Ensure the page is not blocked by Facebook'
            ])
        else:
            suggestions['recovery_suggestions'].extend([
                'Check Chrome DevTools console for errors',
                'Verify Chrome is not in an error state',
                'Try closing and restarting Chrome',
                'Check system resources (CPU, memory)'
            ])
        
        # Log the suggestions
        logger.warning(f"Chrome timeout error: {error}")
        logger.info(f"Recovery suggestions: {suggestions['recovery_suggestions']}")
        
        return suggestions
    
    async def capture_debug_screenshot(self) -> str:
        """
        Capture screenshot for debugging failed extractions.
        
        This is a placeholder that would integrate with Chrome DevTools
        to capture a screenshot when extraction returns empty results.
        
        Returns:
            Path to the saved screenshot or error message
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = f"debug_screenshot_{timestamp}.png"
        
        logger.warning(
            f"Empty extraction results detected. Screenshot capture requested: {screenshot_path}"
        )
        
        # In a real implementation, this would call Chrome DevTools to capture screenshot
        # For now, we log the intent
        logger.info(
            "To capture screenshot, use Chrome DevTools MCP tool: "
            "mcp__chrome-devtools__capture_screenshot"
        )
        
        return screenshot_path
    
    def _log_error(
        self,
        operation_name: str,
        attempt: int,
        max_attempts: int,
        error: Exception,
        args: tuple,
        kwargs: dict
    ) -> None:
        """
        Log error with timestamp, context, and diagnostic data.
        
        Args:
            operation_name: Name of the operation that failed
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            error: The exception that occurred
            args: Positional arguments passed to the operation
            kwargs: Keyword arguments passed to the operation
        """
        # Build context information
        context = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation_name,
            'attempt': f"{attempt}/{max_attempts}",
            'error_type': type(error).__name__,
            'error_message': str(error),
            'args': str(args) if args else 'None',
            'kwargs': {k: str(v) for k, v in kwargs.items()} if kwargs else {}
        }
        
        # Log with full context
        logger.error(
            f"Operation failed: {operation_name} | "
            f"Attempt: {attempt}/{max_attempts} | "
            f"Error: {type(error).__name__}: {str(error)}"
        )
        logger.debug(f"Full error context: {context}")
