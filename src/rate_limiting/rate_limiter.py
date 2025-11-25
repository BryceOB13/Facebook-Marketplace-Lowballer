"""
Rate limiter for marketplace deal scout.

Implements rate limiting to avoid detection and comply with platform policies.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List


class RateLimiter:
    """
    Rate limiter that enforces delays between actions and hourly request limits.
    
    Attributes:
        min_delay_seconds: Minimum delay between actions in seconds
        max_delay_seconds: Maximum delay between actions in seconds
        max_pages_per_hour: Maximum number of pages that can be requested per hour
        request_timestamps: List of timestamps for tracking hourly limits
    """
    
    def __init__(
        self,
        min_delay_seconds: int = 3,
        max_delay_seconds: int = 7,
        max_pages_per_hour: int = 10
    ):
        """
        Initialize rate limiter with configuration.
        
        Args:
            min_delay_seconds: Minimum delay between actions (default: 3)
            max_delay_seconds: Maximum delay between actions (default: 7)
            max_pages_per_hour: Maximum pages per hour (default: 10)
        """
        self.min_delay_seconds = min_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.max_pages_per_hour = max_pages_per_hour
        self.request_timestamps: List[datetime] = []
    
    async def wait_between_actions(self) -> None:
        """
        Wait a random interval between actions to simulate human behavior.
        
        The delay is randomly chosen between min_delay_seconds and max_delay_seconds.
        Uses asyncio.sleep for non-blocking delay.
        """
        delay = self._generate_random_delay()
        await asyncio.sleep(delay)
    
    def check_hourly_limit(self) -> bool:
        """
        Check if the hourly request limit has been reached.
        
        Removes timestamps older than 1 hour and checks if the number of
        requests in the last hour exceeds the limit.
        
        Returns:
            True if under the limit (can make more requests), False if limit reached
        """
        # Remove timestamps older than 1 hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.request_timestamps = [
            ts for ts in self.request_timestamps if ts > one_hour_ago
        ]
        
        # Check if we're under the limit
        return len(self.request_timestamps) < self.max_pages_per_hour
    
    def record_request(self) -> None:
        """
        Record a request timestamp for hourly limit tracking.
        
        Should be called after each page request to track usage.
        """
        self.request_timestamps.append(datetime.now())
    
    def _generate_random_delay(self) -> float:
        """
        Generate a random delay for human-like timing.
        
        Returns:
            Random float between min_delay_seconds and max_delay_seconds
        """
        return random.uniform(self.min_delay_seconds, self.max_delay_seconds)
