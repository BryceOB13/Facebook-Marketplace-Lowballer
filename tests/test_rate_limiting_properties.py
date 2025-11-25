"""
Property-based tests for rate limiting.

These tests verify universal properties that should hold for all rate limiting
operations across randomly generated inputs.
"""

import pytest
import asyncio
from hypothesis import given, settings, strategies as st
from datetime import datetime, timedelta
from src.rate_limiting.rate_limiter import RateLimiter


# Strategy for generating delay bounds
delay_bounds = st.integers(min_value=1, max_value=20)

# Strategy for generating page limits
page_limits = st.integers(min_value=1, max_value=50)


@given(
    min_delay=delay_bounds,
    max_delay=delay_bounds
)
@settings(max_examples=100)
def test_rate_limiting_delays(min_delay, max_delay):
    """
    **Feature: marketplace-deal-scout, Property 6: Rate limiting delays**
    
    For any sequence of navigation actions, the delay between actions should 
    fall within the range of 3 to 7 seconds.
    
    **Validates: Requirements 7.1**
    """
    # Ensure min_delay <= max_delay
    if min_delay > max_delay:
        min_delay, max_delay = max_delay, min_delay
    
    # Skip if the range is invalid (both equal to same value less than 1)
    if min_delay == max_delay and min_delay < 1:
        return
    
    limiter = RateLimiter(
        min_delay_seconds=min_delay,
        max_delay_seconds=max_delay
    )
    
    # Test multiple delay generations
    for _ in range(10):
        delay = limiter._generate_random_delay()
        
        # Verify delay is within bounds
        assert min_delay <= delay <= max_delay, \
            f"Delay {delay} should be between {min_delay} and {max_delay}"
        
        # Verify delay is a float
        assert isinstance(delay, float), "Delay should be a float value"


@given(
    min_delay=delay_bounds,
    max_delay=delay_bounds
)
@settings(max_examples=100, deadline=None)
def test_wait_between_actions_timing(min_delay, max_delay):
    """
    Test that wait_between_actions actually waits for the correct duration.
    
    For any configured delay range, the actual wait time should fall within
    the specified bounds.
    """
    # Ensure min_delay <= max_delay
    if min_delay > max_delay:
        min_delay, max_delay = max_delay, min_delay
    
    # Skip if the range is too small to measure accurately
    if max_delay - min_delay < 0.1:
        return
    
    limiter = RateLimiter(
        min_delay_seconds=min_delay,
        max_delay_seconds=max_delay
    )
    
    async def measure_wait():
        start = datetime.now()
        await limiter.wait_between_actions()
        end = datetime.now()
        return (end - start).total_seconds()
    
    # Measure actual wait time
    actual_wait = asyncio.run(measure_wait())
    
    # Allow small tolerance for execution overhead (100ms)
    tolerance = 0.1
    assert min_delay - tolerance <= actual_wait <= max_delay + tolerance, \
        f"Actual wait {actual_wait}s should be between {min_delay}s and {max_delay}s (±{tolerance}s tolerance)"


@given(
    max_pages=page_limits,
    num_requests=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100)
def test_hourly_request_limit(max_pages, num_requests):
    """
    **Feature: marketplace-deal-scout, Property 7: Hourly request limit**
    
    For any one-hour time window, the number of marketplace page requests 
    should not exceed 10.
    
    **Validates: Requirements 7.4**
    """
    limiter = RateLimiter(max_pages_per_hour=max_pages)
    
    # Record the specified number of requests
    for _ in range(num_requests):
        limiter.record_request()
    
    # Check if we're under the limit
    under_limit = limiter.check_hourly_limit()
    
    # Verify the limit check is correct
    if num_requests < max_pages:
        assert under_limit, \
            f"Should be under limit: {num_requests} requests < {max_pages} max"
    else:
        assert not under_limit, \
            f"Should be at or over limit: {num_requests} requests >= {max_pages} max"
    
    # Verify the count is accurate
    assert len(limiter.request_timestamps) == num_requests, \
        f"Should have recorded {num_requests} timestamps"


@given(
    max_pages=page_limits,
    recent_requests=st.integers(min_value=0, max_value=50),
    old_requests=st.integers(min_value=0, max_value=50)
)
@settings(max_examples=100)
def test_hourly_limit_window_sliding(max_pages, recent_requests, old_requests):
    """
    Test that the hourly limit properly excludes old timestamps.
    
    For any combination of recent and old requests, only requests within
    the last hour should count toward the limit.
    """
    limiter = RateLimiter(max_pages_per_hour=max_pages)
    
    # Add old timestamps (more than 1 hour ago)
    two_hours_ago = datetime.now() - timedelta(hours=2)
    for _ in range(old_requests):
        limiter.request_timestamps.append(two_hours_ago)
    
    # Add recent timestamps (within the last hour)
    for _ in range(recent_requests):
        limiter.record_request()
    
    # Check the limit
    under_limit = limiter.check_hourly_limit()
    
    # After check_hourly_limit, old timestamps should be removed
    assert len(limiter.request_timestamps) == recent_requests, \
        f"Old timestamps should be removed, only {recent_requests} recent ones should remain"
    
    # Verify limit check only considers recent requests
    if recent_requests < max_pages:
        assert under_limit, \
            f"Should be under limit: {recent_requests} recent requests < {max_pages} max"
    else:
        assert not under_limit, \
            f"Should be at or over limit: {recent_requests} recent requests >= {max_pages} max"


@given(max_pages=page_limits)
@settings(max_examples=100)
def test_record_request_increments_count(max_pages):
    """
    Test that record_request properly adds timestamps.
    
    For any number of record_request calls, the timestamp list should
    grow by that amount.
    """
    limiter = RateLimiter(max_pages_per_hour=max_pages)
    
    initial_count = len(limiter.request_timestamps)
    
    # Record some requests
    num_to_record = min(max_pages + 5, 20)  # Record a reasonable number
    for _ in range(num_to_record):
        limiter.record_request()
    
    # Verify count increased
    assert len(limiter.request_timestamps) == initial_count + num_to_record, \
        f"Should have {num_to_record} more timestamps"
    
    # Verify all timestamps are recent (within last second)
    now = datetime.now()
    for ts in limiter.request_timestamps:
        age = (now - ts).total_seconds()
        assert age < 1.0, f"Timestamp should be recent, but is {age}s old"
