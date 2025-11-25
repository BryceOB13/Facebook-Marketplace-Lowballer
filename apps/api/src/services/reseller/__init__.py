"""Reseller services for deal scoring and detection"""

from .scorer import DealScorer
from .hot_deals import HotDealDetector

__all__ = ["DealScorer", "HotDealDetector"]
