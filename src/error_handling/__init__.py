"""
Error handling module for marketplace deal scout.

Provides retry logic, error recovery, and diagnostic capabilities.
"""

from .error_handler import ErrorHandler, RetryConfig

__all__ = ['ErrorHandler', 'RetryConfig']
