"""
Property-based tests for Chrome Navigator.

These tests verify universal properties that should hold for Chrome DevTools
Protocol navigation operations across randomly generated inputs.
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from src.browser_automation.chrome_navigator import ChromeNavigator
from src.error_handling.error_handler import ErrorHandler


# Strategy for generating valid URLs
valid_urls = st.from_regex(
    r'https://www\.facebook\.com/marketplace/search\?query=[a-zA-Z0-9%]+',
    fullmatch=True
)

# Strategy for generating debug ports
debug_ports = st.integers(min_value=1024, max_value=65535)

# Strategy for generating timeout values
timeouts = st.integers(min_value=1000, max_value=120000)

# Strategy for generating event names
events = st.sampled_from(['load', 'networkidle', 'networkidle2', 'domcontentloaded'])


@given(debug_port=debug_ports)
@settings(max_examples=100)
def test_connection_port_correctness(debug_port):
    """
    **Feature: marketplace-deal-scout, Property 23: Connection port correctness**
    
    For any Chrome connection attempt with configured debug_port, the connection 
    should target that port number.
    
    **Validates: Requirements 6.1**
    """
    # Create a mock agent
    mock_agent = MagicMock()
    
    # Create navigator with specific debug port
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port
    )
    
    # Verify that the navigator stores the correct debug port
    assert navigator.debug_port == debug_port, \
        f"Navigator should store the configured debug_port: {navigator.debug_port} != {debug_port}"
    
    # Verify that the debug port is within valid range
    assert 1024 <= debug_port <= 65535, \
        f"Debug port should be in valid range (1024-65535): {debug_port}"


@given(
    debug_port=debug_ports,
    mcp_prefix=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=5,
        max_size=30
    )
)
@settings(max_examples=100)
def test_mcp_tool_prefix_configuration(debug_port, mcp_prefix):
    """
    Test that MCP tool prefix is correctly configured and used.
    
    For any MCP tool prefix, the navigator should store and use that prefix
    when constructing tool names.
    
    **Validates: Requirements 6.1**
    """
    # Create a mock agent
    mock_agent = MagicMock()
    
    # Create navigator with specific MCP prefix
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port,
        mcp_tool_prefix=mcp_prefix
    )
    
    # Verify that the navigator stores the correct MCP prefix
    assert navigator.mcp_tool_prefix == mcp_prefix, \
        f"Navigator should store the configured mcp_tool_prefix: {navigator.mcp_tool_prefix} != {mcp_prefix}"


@pytest.mark.asyncio
@given(
    debug_port=debug_ports,
    url=valid_urls,
    timeout_ms=timeouts
)
@settings(max_examples=50)
async def test_navigate_to_url_calls_correct_tool(debug_port, url, timeout_ms):
    """
    Test that navigate_to_url calls the correct MCP tool with correct parameters.
    
    For any URL and timeout, the navigator should call the navigate_page tool
    with the correct tool name and parameters.
    
    **Validates: Requirements 6.1**
    """
    # Create a mock agent with async call_tool method
    mock_agent = AsyncMock()
    mock_agent.call_tool = AsyncMock(return_value={"success": True})
    
    # Create navigator
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port
    )
    
    # Call navigate_to_url
    result = await navigator.navigate_to_url(url, timeout_ms=timeout_ms)
    
    # Verify the tool was called
    assert mock_agent.call_tool.called, "Agent should call a tool"
    
    # Get the call arguments
    call_args = mock_agent.call_tool.call_args
    tool_name = call_args[0][0] if call_args[0] else call_args.kwargs.get('tool_name')
    tool_params = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('params', {})
    
    # Verify the tool name contains navigate_page
    assert 'navigate_page' in tool_name, \
        f"Tool name should contain 'navigate_page': {tool_name}"
    
    # Verify the parameters include the URL and timeout
    assert tool_params.get('url') == url, \
        f"Tool parameters should include the URL: {tool_params.get('url')} != {url}"
    
    assert tool_params.get('timeout_ms') == timeout_ms, \
        f"Tool parameters should include the timeout: {tool_params.get('timeout_ms')} != {timeout_ms}"


@pytest.mark.asyncio
@given(
    debug_port=debug_ports,
    event=events,
    timeout_ms=timeouts
)
@settings(max_examples=50)
async def test_wait_for_page_load_calls_correct_tool(debug_port, event, timeout_ms):
    """
    Test that wait_for_page_load calls the correct MCP tool with correct parameters.
    
    For any event and timeout, the navigator should call the wait_for tool
    with the correct tool name and parameters.
    
    **Validates: Requirements 6.1**
    """
    # Create a mock agent with async call_tool method
    mock_agent = AsyncMock()
    mock_agent.call_tool = AsyncMock(return_value={"success": True})
    
    # Create navigator
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port
    )
    
    # Call wait_for_page_load
    result = await navigator.wait_for_page_load(event=event, timeout_ms=timeout_ms)
    
    # Verify the tool was called
    assert mock_agent.call_tool.called, "Agent should call a tool"
    
    # Get the call arguments
    call_args = mock_agent.call_tool.call_args
    tool_name = call_args[0][0] if call_args[0] else call_args.kwargs.get('tool_name')
    tool_params = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('params', {})
    
    # Verify the tool name contains wait_for
    assert 'wait_for' in tool_name, \
        f"Tool name should contain 'wait_for': {tool_name}"
    
    # Verify the parameters include the event and timeout
    assert tool_params.get('event') == event, \
        f"Tool parameters should include the event: {tool_params.get('event')} != {event}"
    
    assert tool_params.get('timeout_ms') == timeout_ms, \
        f"Tool parameters should include the timeout: {tool_params.get('timeout_ms')} != {timeout_ms}"


@pytest.mark.asyncio
@given(debug_port=debug_ports)
@settings(max_examples=50)
async def test_dismiss_login_modal_calls_evaluate_script(debug_port):
    """
    Test that dismiss_login_modal calls the evaluate_script tool.
    
    For any debug port, the navigator should call the evaluate_script tool
    when dismissing login modals.
    
    **Validates: Requirements 6.3**
    """
    # Create a mock agent with async call_tool method
    mock_agent = AsyncMock()
    mock_agent.call_tool = AsyncMock(return_value={"success": True})
    
    # Create navigator
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port
    )
    
    # Call dismiss_login_modal
    result = await navigator.dismiss_login_modal()
    
    # Verify the tool was called
    assert mock_agent.call_tool.called, "Agent should call a tool"
    
    # Get the call arguments
    call_args = mock_agent.call_tool.call_args
    tool_name = call_args[0][0] if call_args[0] else call_args.kwargs.get('tool_name')
    
    # Verify the tool name contains evaluate_script
    assert 'evaluate_script' in tool_name, \
        f"Tool name should contain 'evaluate_script': {tool_name}"


@pytest.mark.asyncio
@given(
    debug_port=debug_ports,
    url=valid_urls
)
@settings(max_examples=50)
async def test_navigate_and_wait_calls_both_operations(debug_port, url):
    """
    Test that navigate_and_wait calls both navigate and wait operations.
    
    For any URL, the navigator should call both navigate_to_url and 
    wait_for_page_load operations.
    
    **Validates: Requirements 1.2**
    """
    # Create a mock agent with async call_tool method
    mock_agent = AsyncMock()
    mock_agent.call_tool = AsyncMock(return_value={"success": True})
    
    # Create navigator
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port
    )
    
    # Call navigate_and_wait
    result = await navigator.navigate_and_wait(url)
    
    # Verify the tool was called multiple times (navigate, wait, evaluate for modal)
    assert mock_agent.call_tool.call_count >= 2, \
        f"Agent should call tools for both navigate and wait: {mock_agent.call_tool.call_count} calls"
    
    # Get all tool names called
    tool_names = [call[0][0] for call in mock_agent.call_tool.call_args_list]
    
    # Verify both navigate_page and wait_for were called
    has_navigate = any('navigate_page' in name for name in tool_names)
    has_wait = any('wait_for' in name for name in tool_names)
    
    assert has_navigate, "Should call navigate_page tool"
    assert has_wait, "Should call wait_for tool"


@pytest.mark.asyncio
@given(debug_port=debug_ports)
@settings(max_examples=50)
async def test_error_handler_integration(debug_port):
    """
    Test that ChromeNavigator integrates with ErrorHandler for retry logic.
    
    For any debug port, the navigator should use ErrorHandler for retry logic
    on navigation failures.
    
    **Validates: Requirements 1.5, 8.1**
    """
    # Create a mock agent
    mock_agent = AsyncMock()
    
    # Create a custom error handler
    error_handler = ErrorHandler(max_retries=2)
    
    # Create navigator with error handler
    navigator = ChromeNavigator(
        agent=mock_agent,
        debug_port=debug_port,
        error_handler=error_handler
    )
    
    # Verify the error handler is stored
    assert navigator.error_handler is error_handler, \
        "Navigator should store the provided error handler"
    
    # Verify error handler has correct configuration
    assert navigator.error_handler.config.max_retries == 2, \
        "Error handler should have correct max_retries"
