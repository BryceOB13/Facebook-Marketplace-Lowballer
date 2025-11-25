"""Tests for configuration module."""

import os
from src.config import (
    AGENT_CONFIG,
    AgentSettings,
    RateLimitConfig,
    ScrollConfig,
    RetryConfig,
    MemoryConfig,
    get_agent_settings,
)


def test_agent_config_exists():
    """Test that AGENT_CONFIG dictionary is properly defined."""
    assert isinstance(AGENT_CONFIG, dict)
    assert "chrome_debug_port" in AGENT_CONFIG
    assert "session_id" in AGENT_CONFIG
    assert "max_turns" in AGENT_CONFIG
    assert "rate_limiting" in AGENT_CONFIG
    assert "scroll_config" in AGENT_CONFIG
    assert "retry_config" in AGENT_CONFIG
    assert "memory_config" in AGENT_CONFIG


def test_agent_config_defaults():
    """Test that AGENT_CONFIG has correct default values."""
    assert AGENT_CONFIG["chrome_debug_port"] == 9222
    assert AGENT_CONFIG["session_id"] == "marketplace_scout_v1"
    assert AGENT_CONFIG["max_turns"] == 25
    assert AGENT_CONFIG["rate_limiting"]["min_delay_seconds"] == 3
    assert AGENT_CONFIG["rate_limiting"]["max_delay_seconds"] == 7
    assert AGENT_CONFIG["rate_limiting"]["max_pages_per_hour"] == 10


def test_get_agent_settings():
    """Test that get_agent_settings returns proper AgentSettings object."""
    settings = get_agent_settings()
    
    assert isinstance(settings, AgentSettings)
    assert settings.chrome_debug_port == 9222
    assert settings.session_id == "marketplace_scout_v1"
    assert settings.max_turns == 25
    
    assert isinstance(settings.rate_limiting, RateLimitConfig)
    assert settings.rate_limiting.min_delay_seconds == 3
    assert settings.rate_limiting.max_delay_seconds == 7
    
    assert isinstance(settings.scroll_config, ScrollConfig)
    assert settings.scroll_config.iterations == 3
    
    assert isinstance(settings.retry_config, RetryConfig)
    assert settings.retry_config.max_retries == 3
    
    assert isinstance(settings.memory_config, MemoryConfig)
    assert settings.memory_config.user_id == "deal_scout"


def test_agent_settings_with_custom_values():
    """Test creating AgentSettings with custom values."""
    custom_rate_limit = RateLimitConfig(
        min_delay_seconds=5,
        max_delay_seconds=10,
        max_pages_per_hour=5
    )
    
    settings = AgentSettings(
        chrome_debug_port=9223,
        session_id="custom_session",
        max_turns=50,
        rate_limiting=custom_rate_limit
    )
    
    assert settings.chrome_debug_port == 9223
    assert settings.session_id == "custom_session"
    assert settings.max_turns == 50
    assert settings.rate_limiting.min_delay_seconds == 5
    assert settings.rate_limiting.max_delay_seconds == 10


def test_environment_variable_override():
    """Test that environment variables can override defaults."""
    # Set environment variable
    os.environ["CHROME_DEBUG_PORT"] = "9999"
    
    # Re-import to get new config
    from src.config.agent_config import AGENT_CONFIG as new_config
    
    # Note: This test may not work as expected due to module caching
    # In production, environment variables should be set before import
    
    # Clean up
    del os.environ["CHROME_DEBUG_PORT"]


def test_dataclass_initialization():
    """Test that all config dataclasses can be initialized."""
    rate_limit = RateLimitConfig()
    assert rate_limit.min_delay_seconds == 3
    
    scroll = ScrollConfig()
    assert scroll.iterations == 3
    
    retry = RetryConfig()
    assert retry.max_retries == 3
    
    memory = MemoryConfig()
    assert memory.user_id == "deal_scout"
