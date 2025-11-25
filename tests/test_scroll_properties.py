"""
Property-based tests for scroll handler.

These tests verify universal properties that should hold for scroll operations,
including delay bounds and iteration counts.
"""

import pytest
from hypothesis import given, settings, strategies as st
import re
import asyncio

from src.scroll_handler import ScrollHandler


# Strategy for scroll iterations
scroll_iterations = st.integers(min_value=1, max_value=10)

# Strategy for delay bounds
delay_bounds = st.integers(min_value=1000, max_value=10000)


@given(
    scroll_iterations=scroll_iterations,
    min_delay=delay_bounds,
    max_delay=delay_bounds
)
@settings(max_examples=100)
def test_scroll_delay_bounds(scroll_iterations, min_delay, max_delay):
    """
    **Feature: marketplace-deal-scout, Property 13: Scroll delay bounds**
    
    For any scroll operation, the delay after scrolling should be between 
    2.0 and 4.5 seconds (or the configured min/max delay bounds).
    
    **Validates: Requirements 3.2**
    """
    # Ensure min_delay <= max_delay
    if min_delay > max_delay:
        min_delay, max_delay = max_delay, min_delay
    
    # Create scroll handler with configured delays
    handler = ScrollHandler(
        scroll_iterations=scroll_iterations,
        min_delay_ms=min_delay,
        max_delay_ms=max_delay
    )
    
    # Generate the scroll script
    script = handler._generate_scroll_script()
    
    # Verify the script contains the correct delay bounds
    assert str(min_delay) in script, \
        f"Script should contain min_delay value {min_delay}"
    assert str(max_delay) in script, \
        f"Script should contain max_delay value {max_delay}"
    
    # Extract the delay calculation from the script
    # Pattern: const delay = MIN + Math.random() * (MAX - MIN);
    delay_pattern = re.search(
        r'const delay = (\d+) \+ Math\.random\(\) \* \((\d+) - (\d+)\)',
        script
    )
    
    assert delay_pattern is not None, "Script should contain delay calculation"
    
    script_min = int(delay_pattern.group(1))
    script_max_part1 = int(delay_pattern.group(2))
    script_max_part2 = int(delay_pattern.group(3))
    
    # Verify the delay bounds in the script
    assert script_min == min_delay, \
        f"Script min delay {script_min} should match configured {min_delay}"
    assert script_max_part1 == max_delay, \
        f"Script max delay {script_max_part1} should match configured {max_delay}"
    assert script_max_part2 == min_delay, \
        f"Script should subtract min_delay {script_max_part2} from max_delay"
    
    # Test the get_random_delay method
    for _ in range(10):
        random_delay = handler.get_random_delay()
        assert min_delay <= random_delay <= max_delay, \
            f"Random delay {random_delay} should be between {min_delay} and {max_delay}"


@given(scroll_iterations=scroll_iterations)
@settings(max_examples=100)
def test_scroll_iteration_count(scroll_iterations):
    """
    **Feature: marketplace-deal-scout, Property 14: Scroll iteration count**
    
    For any configured scroll_iterations value N, the scroll handler should 
    execute exactly N scroll-and-wait cycles.
    
    **Validates: Requirements 3.3**
    """
    # Create scroll handler with configured iterations
    handler = ScrollHandler(
        scroll_iterations=scroll_iterations,
        min_delay_ms=2000,
        max_delay_ms=4500
    )
    
    # Generate the scroll script
    script = handler._generate_scroll_script()
    
    # Verify the script contains the correct iteration count
    assert str(scroll_iterations) in script, \
        f"Script should contain scroll_iterations value {scroll_iterations}"
    
    # Extract the for loop iteration count from the script
    # Pattern: for (let i = 0; i < N; i++)
    loop_pattern = re.search(
        r'for \(let i = 0; i < (\d+); i\+\+\)',
        script
    )
    
    assert loop_pattern is not None, "Script should contain for loop"
    
    script_iterations = int(loop_pattern.group(1))
    
    # Verify the iteration count matches
    assert script_iterations == scroll_iterations, \
        f"Script iterations {script_iterations} should match configured {scroll_iterations}"
    
    # Verify the script scrolls to document.body.scrollHeight
    assert 'window.scrollTo(0, document.body.scrollHeight)' in script, \
        "Script should scroll to document.body.scrollHeight"
    
    # Verify the script has the scrollAndWait function
    assert 'const scrollAndWait = async () =>' in script, \
        "Script should define scrollAndWait function"
    
    # Verify the script calls scrollAndWait in the loop
    assert 'await scrollAndWait()' in script, \
        "Script should call scrollAndWait in the loop"


@given(
    scroll_iterations=scroll_iterations,
    min_delay=st.integers(min_value=2000, max_value=2000),
    max_delay=st.integers(min_value=4500, max_value=4500)
)
@settings(max_examples=100)
def test_default_delay_bounds(scroll_iterations, min_delay, max_delay):
    """
    Test that default delay bounds match requirements (2.0 to 4.5 seconds).
    
    For the default configuration, delays should be between 2000ms and 4500ms
    as specified in Requirements 3.2.
    """
    # Create handler with default delays
    handler = ScrollHandler(scroll_iterations=scroll_iterations)
    
    # Verify default values
    assert handler.min_delay_ms == 2000, "Default min_delay should be 2000ms"
    assert handler.max_delay_ms == 4500, "Default max_delay should be 4500ms"
    
    # Test random delays are within bounds
    for _ in range(10):
        delay = handler.get_random_delay()
        assert 2000 <= delay <= 4500, \
            f"Default random delay {delay} should be between 2000ms and 4500ms"


# Edge case tests

def test_scroll_script_structure():
    """
    Test that the generated scroll script has the correct structure.
    
    Verifies that the script is an async IIFE that returns a completion message.
    """
    handler = ScrollHandler(scroll_iterations=3)
    script = handler._generate_scroll_script()
    
    # Verify it's an async IIFE
    assert script.strip().startswith('async () => {'), \
        "Script should be an async arrow function"
    assert script.strip().endswith('}'), \
        "Script should end with closing brace"
    
    # Verify it returns a completion message
    assert "return 'Scrolling complete'" in script, \
        "Script should return completion message"
    
    # Verify it uses Promise for delays
    assert 'await new Promise(r => setTimeout(r, delay))' in script, \
        "Script should use Promise-based delays"


@pytest.mark.asyncio
async def test_scroll_and_load_execution():
    """
    Test that scroll_and_load executes the script and returns True.
    
    Uses a mock execute function to verify the script is called correctly.
    """
    handler = ScrollHandler(scroll_iterations=2, min_delay_ms=100, max_delay_ms=200)
    
    # Track if the script was executed
    executed_script = None
    
    async def mock_execute_script(script):
        nonlocal executed_script
        executed_script = script
        return "Scrolling complete"
    
    # Execute scroll_and_load
    result = await handler.scroll_and_load(mock_execute_script)
    
    # Verify it returned True
    assert result is True, "scroll_and_load should return True on success"
    
    # Verify the script was executed
    assert executed_script is not None, "Script should have been executed"
    assert 'window.scrollTo(0, document.body.scrollHeight)' in executed_script, \
        "Executed script should contain scroll command"


@pytest.mark.asyncio
async def test_scroll_and_load_error_handling():
    """
    Test that scroll_and_load raises RuntimeError on script execution failure.
    """
    handler = ScrollHandler(scroll_iterations=1)
    
    async def mock_execute_script_error(script):
        raise Exception("Script execution failed")
    
    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to execute scroll script"):
        await handler.scroll_and_load(mock_execute_script_error)
