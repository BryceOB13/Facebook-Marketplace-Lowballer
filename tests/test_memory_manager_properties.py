"""
Property-based tests for memory manager.

These tests verify universal properties that should hold across all valid
executions of the memory manager operations.
"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import asyncio

from src.models import Listing
from src.memory.memory_manager import DealMemoryManager


# Strategy for generating valid listing IDs (numeric strings)
listing_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)),
    min_size=10,
    max_size=20
)

# Strategy for generating titles
titles = st.text(min_size=10, max_size=200)

# Strategy for generating price strings with currency symbols
prices = st.builds(
    lambda val: f"${val:,}",
    st.integers(min_value=1, max_value=100000)
)

# Strategy for generating locations
locations = st.from_regex(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*, [A-Z]{2}', fullmatch=True)

# Strategy for generating image URLs
image_urls = st.from_regex(r'https://[a-z0-9\-\.]+\.(jpg|png|jpeg)', fullmatch=True)

# Strategy for generating marketplace URLs
marketplace_urls = st.builds(
    lambda id: f"https://www.facebook.com/marketplace/item/{id}/",
    listing_ids
)

# Strategy for generating datetimes
datetimes = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
)

# Strategy for generating complete Listing objects
listings = st.builds(
    Listing,
    id=listing_ids,
    title=titles,
    price=prices,
    location=locations,
    image_url=image_urls,
    url=marketplace_urls,
    scraped_at=datetimes
)

# Strategy for generating categories
categories = st.text(min_size=1, max_size=50)


def run_async(coro):
    """Helper to run async functions in tests."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@given(listing=listings, category=categories)
@settings(max_examples=100)
def test_storage_field_completeness(listing, category):
    """
    **Feature: marketplace-deal-scout, Property 15: Storage field completeness**
    
    For any listing stored in memory, the stored record must contain listing ID, 
    title, price, location, and timestamp fields.
    
    **Validates: Requirements 4.1**
    """
    # Create a mock mem0_tool that captures what was stored
    stored_data = {}
    
    async def mock_mem0_tool(content=None, user_id=None, metadata=None, **kwargs):
        stored_data['content'] = content
        stored_data['user_id'] = user_id
        stored_data['metadata'] = metadata
        return True
    
    # Create manager with mock tool
    manager = DealMemoryManager(user_id="test_user", mem0_tool=mock_mem0_tool)
    
    # Store the listing
    result = run_async(manager.store_listing(listing, category))
    
    # Verify storage was successful
    assert result is True, "Storage should succeed"
    
    # Verify content contains all required fields
    content = stored_data.get('content', '')
    assert listing.id in content, f"Content must contain listing ID {listing.id}"
    assert listing.title in content, f"Content must contain title {listing.title}"
    assert listing.price in content, f"Content must contain price {listing.price}"
    assert listing.location in content, f"Content must contain location {listing.location}"
    
    # Verify metadata contains timestamp
    metadata = stored_data.get('metadata', {})
    assert 'stored_at' in metadata, "Metadata must contain stored_at timestamp"
    assert metadata['stored_at'] is not None, "stored_at must not be None"


@given(listing=listings, category=categories)
@settings(max_examples=100)
def test_metadata_completeness(listing, category):
    """
    **Feature: marketplace-deal-scout, Property 16: Metadata completeness**
    
    For any listing stored in memory, the metadata must include category, 
    price_range, and listing_id fields.
    
    **Validates: Requirements 4.2**
    """
    # Create a mock mem0_tool that captures what was stored
    stored_data = {}
    
    async def mock_mem0_tool(content=None, user_id=None, metadata=None, **kwargs):
        stored_data['content'] = content
        stored_data['user_id'] = user_id
        stored_data['metadata'] = metadata
        return True
    
    # Create manager with mock tool
    manager = DealMemoryManager(user_id="test_user", mem0_tool=mock_mem0_tool)
    
    # Store the listing
    result = run_async(manager.store_listing(listing, category))
    
    # Verify storage was successful
    assert result is True, "Storage should succeed"
    
    # Verify metadata contains all required fields
    metadata = stored_data.get('metadata', {})
    assert 'category' in metadata, "Metadata must contain category"
    assert metadata['category'] == category, f"Category should be {category}"
    
    assert 'price_range' in metadata, "Metadata must contain price_range"
    assert metadata['price_range'] is not None, "price_range must not be None"
    
    assert 'listing_id' in metadata, "Metadata must contain listing_id"
    assert metadata['listing_id'] == listing.id, f"listing_id should be {listing.id}"


@given(listing_id=listing_ids)
@settings(max_examples=100)
def test_new_listing_detection(listing_id):
    """
    **Feature: marketplace-deal-scout, Property 18: New listing detection**
    
    For any listing with an ID not present in memory, the comparison operation 
    should flag it as a new deal.
    
    **Validates: Requirements 4.4**
    """
    # Create a mock mem0_tool that returns empty results (listing not in memory)
    async def mock_mem0_tool_empty(query=None, user_id=None, **kwargs):
        return []
    
    # Create manager with mock tool
    manager = DealMemoryManager(user_id="test_user", mem0_tool=mock_mem0_tool_empty)
    
    # Check if listing is new
    is_new = run_async(manager.check_if_new(listing_id))
    
    # Should be flagged as new since memory returned empty results
    assert is_new is True, "Listing should be flagged as new when not in memory"


@given(listing_id=listing_ids, old_price=prices, new_price=prices)
@settings(max_examples=100)
def test_price_change_detection(listing_id, old_price, new_price):
    """
    **Feature: marketplace-deal-scout, Property 19: Price change detection**
    
    For any listing ID that exists in memory with price P1, if the current listing 
    has price P2 where P1 ≠ P2, the system should flag it as a price change and 
    return both prices.
    
    **Validates: Requirements 4.5**
    """
    # Create a mock mem0_tool that returns a stored record with old_price
    location = "New York, NY"
    title = "Test Item"
    stored_content = f"Found {title}, {old_price}, {location} - listing ID {listing_id}"
    
    async def mock_mem0_tool_with_record(query=None, user_id=None, **kwargs):
        return [{'content': stored_content}]
    
    # Create manager with mock tool
    manager = DealMemoryManager(user_id="test_user", mem0_tool=mock_mem0_tool_with_record)
    
    # Detect price change
    result = run_async(manager.detect_price_change(listing_id, new_price))
    
    if old_price == new_price:
        # If prices are the same, should return None
        assert result is None, "Should return None when prices are the same"
    else:
        # If prices differ, should return tuple of (old_price, new_price)
        assert result is not None, "Should detect price change when prices differ"
        assert isinstance(result, tuple), "Result should be a tuple"
        assert len(result) == 2, "Result tuple should have 2 elements"
        assert result[0] == old_price, f"First element should be old price {old_price}"
        assert result[1] == new_price, f"Second element should be new price {new_price}"


@given(listing_id=listing_ids)
@settings(max_examples=100)
def test_price_change_detection_not_found(listing_id):
    """
    Test that price change detection returns None when listing not in memory.
    
    For any listing ID not in memory, detect_price_change should return None.
    """
    # Create a mock mem0_tool that returns empty results
    async def mock_mem0_tool_empty(query=None, user_id=None, **kwargs):
        return []
    
    # Create manager with mock tool
    manager = DealMemoryManager(user_id="test_user", mem0_tool=mock_mem0_tool_empty)
    
    # Detect price change
    result = run_async(manager.detect_price_change(listing_id, "$100"))
    
    # Should return None since listing not in memory
    assert result is None, "Should return None when listing not in memory"
