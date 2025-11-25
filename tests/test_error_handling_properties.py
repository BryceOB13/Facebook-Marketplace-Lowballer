"""
Property-based tests for error handling.

These tests verify universal properties that should hold for all error handling
operations across randomly generated inputs.
"""

import pytest
import asyncio
from unittest.mock import patch
from hypothesis import given, settings, strategies as st
from src.error_handling.error_handler import ErrorHandler, RetryConfig


# Strategy for generating retry configuration values
retry_counts = st.integers(min_value=1, max_value=10)
timeout_values = st.integers(min_value=1000, max_value=60000)
multiplier_values = st.floats(min_value=1.1, max_value=3.0)
attempt_numbers = st.integers(min_value=0, max_value=9)


@given(
    initial_timeout=timeout_values,
    multiplier=multiplier_values,
    attempt=attempt_numbers
)
@settings(max_examples=100)
def test_retry_timeout_escalation(initial_timeout, multiplier, attempt):
    """
    **Feature: marketplace-deal-scout, Property 5: Retry timeout escalation**
    
    For any navigation timeout error, the retry attempt should use a timeout 
    value greater than the previous attempt.
    
    **Validates: Requirements 1.5**
    """
    config = RetryConfig(
        initial_timeout_ms=initial_timeout,
        timeout_multiplier=multiplier
    )
    
    # Get timeout for current attempt
    current_timeout = config.get_timeout(attempt)
    
    # Verify timeout is calculated correctly
    expected_timeout = int(initial_timeout * (multiplier ** attempt))
    assert current_timeout == expected_timeout, \
        f"Timeout for attempt {attempt} should be {expected_timeout}, got {current_timeout}"
    
    # If there's a next attempt, verify escalation
    if attempt < 9:  # Reasonable upper bound
        next_timeout = config.get_timeout(attempt + 1)
        
        # Next timeout should be strictly greater than current (escalation property)
        assert next_timeout > current_timeout, \
            f"Timeout should escalate: attempt {attempt + 1} timeout ({next_timeout}ms) " \
            f"should be > attempt {attempt} timeout ({current_timeout}ms)"
        
        # Verify the escalation follows the multiplier
        expected_ratio = multiplier
        actual_ratio = next_timeout / current_timeout
        
        # Allow small floating point tolerance
        tolerance = 0.01
        assert abs(actual_ratio - expected_ratio) < tolerance, \
            f"Escalation ratio should be {expected_ratio}, got {actual_ratio}"


@given(
    initial_timeout=timeout_values,
    multiplier=multiplier_values
)
@settings(max_examples=100)
def test_timeout_sequence_monotonic_increasing(initial_timeout, multiplier):
    """
    Test that timeout values form a monotonically increasing sequence.
    
    For any retry configuration, each successive timeout should be greater
    than or equal to the previous one.
    """
    config = RetryConfig(
        initial_timeout_ms=initial_timeout,
        timeout_multiplier=multiplier
    )
    
    # Generate a sequence of timeouts
    timeouts = [config.get_timeout(i) for i in range(5)]
    
    # Verify monotonic increasing property
    for i in range(len(timeouts) - 1):
        assert timeouts[i + 1] > timeouts[i], \
            f"Timeout sequence should be strictly increasing: " \
            f"timeout[{i + 1}] ({timeouts[i + 1]}) should be > timeout[{i}] ({timeouts[i]})"


@given(
    max_retries=retry_counts,
    multiplier=multiplier_values
)
@settings(max_examples=100, deadline=None)
def test_retry_exhaustion_termination(max_retries, multiplier):
    """
    **Feature: marketplace-deal-scout, Property 26: Retry exhaustion termination**
    
    For any operation that fails max_retries times, the system should terminate 
    and report the failure reason.
    
    **Validates: Requirements 8.5**
    """
    handler = ErrorHandler(
        max_retries=max_retries,
        timeout_multiplier=multiplier
    )
    
    # Create a function that always fails
    call_count = 0
    
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError(f"Simulated failure #{call_count}")
    
    # Mock asyncio.sleep to avoid delays during testing
    with patch('asyncio.sleep', return_value=None):
        # Attempt the operation with retry logic
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(handler.retry_with_backoff(always_fails))
    
    # Verify the operation was attempted exactly max_retries times
    assert call_count == max_retries, \
        f"Operation should be attempted exactly {max_retries} times, was attempted {call_count} times"
    
    # Verify the exception message contains information about the failure
    assert "Simulated failure" in str(exc_info.value), \
        "Exception should contain the failure reason"
    
    # Verify it's the last failure that's raised
    assert f"#{max_retries}" in str(exc_info.value), \
        f"Should raise the last failure (#{max_retries})"


@given(
    max_retries=retry_counts,
    success_on_attempt=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
def test_retry_succeeds_before_exhaustion(max_retries, success_on_attempt):
    """
    Test that retry logic returns successfully when operation succeeds
    before exhausting retries.
    
    For any operation that succeeds on attempt N where N <= max_retries,
    the retry logic should return the result without further attempts.
    """
    # Only test cases where success happens within retry limit
    if success_on_attempt > max_retries:
        return
    
    handler = ErrorHandler(max_retries=max_retries)
    
    call_count = 0
    
    async def fails_then_succeeds():
        nonlocal call_count
        call_count += 1
        if call_count < success_on_attempt:
            raise ValueError(f"Failure #{call_count}")
        return f"Success on attempt {call_count}"
    
    # Mock asyncio.sleep to avoid delays during testing
    with patch('asyncio.sleep', return_value=None):
        # Should succeed without raising
        result = asyncio.run(handler.retry_with_backoff(fails_then_succeeds))
    
    # Verify it succeeded on the expected attempt
    assert call_count == success_on_attempt, \
        f"Should succeed on attempt {success_on_attempt}, actually succeeded on {call_count}"
    
    # Verify the result is correct
    assert result == f"Success on attempt {success_on_attempt}", \
        f"Should return success message"


@given(
    attempt=attempt_numbers
)
@settings(max_examples=100)
def test_backoff_delay_exponential_growth(attempt):
    """
    Test that backoff delays grow exponentially.
    
    For any retry attempt, the backoff delay should follow exponential
    growth pattern: delay = 2.0 * (2 ^ attempt)
    """
    config = RetryConfig()
    
    delay = config.get_backoff_delay(attempt)
    
    # Verify delay calculation
    expected_delay = 2.0 * (2 ** attempt)
    assert delay == expected_delay, \
        f"Backoff delay for attempt {attempt} should be {expected_delay}s, got {delay}s"
    
    # If there's a next attempt, verify exponential growth
    if attempt < 9:
        next_delay = config.get_backoff_delay(attempt + 1)
        
        # Next delay should be exactly double the current delay
        assert next_delay == delay * 2, \
            f"Backoff delay should double: attempt {attempt + 1} delay ({next_delay}s) " \
            f"should be 2x attempt {attempt} delay ({delay}s)"


@given(
    max_retries=retry_counts
)
@settings(max_examples=100)
def test_backoff_delays_increase_monotonically(max_retries):
    """
    Test that backoff delays form a monotonically increasing sequence.
    
    For any retry configuration, each successive backoff delay should be
    greater than the previous one.
    """
    config = RetryConfig(max_retries=max_retries)
    
    # Generate sequence of backoff delays
    delays = [config.get_backoff_delay(i) for i in range(max_retries)]
    
    # Verify monotonic increasing
    for i in range(len(delays) - 1):
        assert delays[i + 1] > delays[i], \
            f"Backoff delays should increase: delay[{i + 1}] ({delays[i + 1]}s) " \
            f"should be > delay[{i}] ({delays[i]}s)"


@given(
    initial_timeout=timeout_values,
    multiplier=multiplier_values,
    max_retries=retry_counts
)
@settings(max_examples=100)
def test_timeout_always_positive(initial_timeout, multiplier, max_retries):
    """
    Test that calculated timeouts are always positive integers.
    
    For any valid configuration, all timeout values should be positive.
    """
    config = RetryConfig(
        initial_timeout_ms=initial_timeout,
        timeout_multiplier=multiplier,
        max_retries=max_retries
    )
    
    # Check timeouts for all possible attempts
    for attempt in range(max_retries):
        timeout = config.get_timeout(attempt)
        
        # Verify timeout is positive
        assert timeout > 0, \
            f"Timeout for attempt {attempt} should be positive, got {timeout}"
        
        # Verify timeout is an integer
        assert isinstance(timeout, int), \
            f"Timeout should be an integer, got {type(timeout)}"
