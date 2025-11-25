"""Agent configuration settings for Marketplace Deal Scout."""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    min_delay_seconds: int = 3
    max_delay_seconds: int = 7
    max_pages_per_hour: int = 10


@dataclass
class ScrollConfig:
    """Scroll behavior configuration."""
    iterations: int = 3
    min_delay_ms: int = 2000
    max_delay_ms: int = 4500


@dataclass
class RetryConfig:
    """Retry and error handling configuration."""
    max_retries: int = 3
    initial_timeout_ms: int = 30000
    timeout_multiplier: float = 1.5


@dataclass
class MemoryConfig:
    """Memory persistence configuration."""
    user_id: str = "deal_scout"
    storage_type: str = "file"
    base_dir: str = "./agent_sessions"


@dataclass
class AgentSettings:
    """Main agent configuration settings."""
    chrome_debug_port: int = 9222
    session_id: str = "marketplace_scout_v1"
    max_turns: int = 50
    rate_limiting: RateLimitConfig = None
    scroll_config: ScrollConfig = None
    retry_config: RetryConfig = None
    memory_config: MemoryConfig = None
    
    def __post_init__(self):
        """Initialize nested configs if not provided."""
        if self.rate_limiting is None:
            self.rate_limiting = RateLimitConfig()
        if self.scroll_config is None:
            self.scroll_config = ScrollConfig()
        if self.retry_config is None:
            self.retry_config = RetryConfig()
        if self.memory_config is None:
            self.memory_config = MemoryConfig()


# Default agent configuration
AGENT_CONFIG = {
    "chrome_debug_port": int(os.getenv("CHROME_DEBUG_PORT", "9222")),
    "session_id": os.getenv("SESSION_ID", "marketplace_scout_v1"),
    "max_turns": int(os.getenv("MAX_TURNS", "25")),
    "rate_limiting": {
        "min_delay_seconds": int(os.getenv("MIN_DELAY_SECONDS", "3")),
        "max_delay_seconds": int(os.getenv("MAX_DELAY_SECONDS", "7")),
        "max_pages_per_hour": int(os.getenv("MAX_PAGES_PER_HOUR", "10")),
    },
    "scroll_config": {
        "iterations": int(os.getenv("SCROLL_ITERATIONS", "3")),
        "min_delay_ms": int(os.getenv("SCROLL_MIN_DELAY_MS", "2000")),
        "max_delay_ms": int(os.getenv("SCROLL_MAX_DELAY_MS", "4500")),
    },
    "retry_config": {
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "initial_timeout_ms": int(os.getenv("INITIAL_TIMEOUT_MS", "30000")),
        "timeout_multiplier": float(os.getenv("TIMEOUT_MULTIPLIER", "1.5")),
    },
    "memory_config": {
        "user_id": os.getenv("MEMORY_USER_ID", "deal_scout"),
        "storage_type": os.getenv("STORAGE_TYPE", "file"),
        "base_dir": os.getenv("SESSION_BASE_DIR", "./agent_sessions"),
    },
}


def get_agent_settings() -> AgentSettings:
    """Get agent settings from configuration."""
    return AgentSettings(
        chrome_debug_port=AGENT_CONFIG["chrome_debug_port"],
        session_id=AGENT_CONFIG["session_id"],
        max_turns=AGENT_CONFIG["max_turns"],
        rate_limiting=RateLimitConfig(**AGENT_CONFIG["rate_limiting"]),
        scroll_config=ScrollConfig(**AGENT_CONFIG["scroll_config"]),
        retry_config=RetryConfig(**AGENT_CONFIG["retry_config"]),
        memory_config=MemoryConfig(**AGENT_CONFIG["memory_config"]),
    )
