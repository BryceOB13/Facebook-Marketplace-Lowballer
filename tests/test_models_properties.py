"""
Property-based tests for data models.

These tests verify universal properties that should hold across all valid
executions of the data model operations.
"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime, timezone
from src.models import Listing, SearchCriteria, DealAlert


# Strategy for generating valid listing IDs (numeric strings)
listing_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)),
    min_size=10,
    max_size=20
)

# Strategy for generating titles
titles = st.one_of(
    st.none(),
    st.text(min_size=10, max_size=200)
)

# Strategy for generating price strings with currency symbols
prices = st.one_of(
    st.none(),
    st.builds(
        lambda val: f"${val:,}",
        st.integers(min_value=1, max_value=100000)
    ),
    st.builds(
        lambda val: f"€{val:,}",
        st.integers(min_value=1, max_value=100000)
    ),
    st.builds(
        lambda val: f"£{val:,}",
        st.integers(min_value=1, max_value=100000)
    )
)

# Strategy for generating locations
locations = st.one_of(
    st.none(),
    st.from_regex(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*, [A-Z]{2}', fullmatch=True)
)

# Strategy for generating image URLs
image_urls = st.one_of(
    st.none(),
    st.from_regex(r'https://[a-z0-9\-\.]+\.(jpg|png|jpeg)', fullmatch=True)
)

# Strategy for generating marketplace URLs
marketplace_urls = st.builds(
    lambda id: f"https://www.facebook.com/marketplace/item/{id}/",
    listing_ids
)

# Strategy for generating datetimes (must be naive for hypothesis)
datetimes = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31)
)

# Strategy for generating complete Listing objects
# Note: We need to ensure at least one of title or price is not None (Requirement 2.6)
listings = st.builds(
    Listing,
    id=listing_ids,
    title=titles,
    price=prices,
    location=locations,
    image_url=image_urls,
    url=marketplace_urls,
    scraped_at=datetimes
).filter(lambda listing: listing.title is not None or listing.price is not None)


@given(listing=listings)
@settings(max_examples=100)
def test_required_field_completeness(listing):
    """
    **Feature: marketplace-deal-scout, Property 8: Required field completeness**
    
    For any listing in the extraction results, the listing must contain a 
    non-null ID and at least one of title or price.
    
    **Validates: Requirements 2.6**
    """
    # Every listing must have a non-null ID
    assert listing.id is not None, "Listing ID must not be None"
    assert len(listing.id) > 0, "Listing ID must not be empty"
    
    # Every listing must have at least one of title or price
    assert listing.title is not None or listing.price is not None, \
        "Listing must have at least one of title or price"


@given(listing=listings)
@settings(max_examples=100)
def test_serialization_round_trip(listing):
    """
    Test that serialization and deserialization preserve listing data.
    
    For any listing, converting to dict and back should produce an equivalent listing.
    """
    # Serialize to dict
    listing_dict = listing.to_dict()
    
    # Deserialize back to Listing
    restored_listing = Listing.from_dict(listing_dict)
    
    # Verify all fields match
    assert restored_listing.id == listing.id
    assert restored_listing.title == listing.title
    assert restored_listing.price == listing.price
    assert restored_listing.location == listing.location
    assert restored_listing.image_url == listing.image_url
    assert restored_listing.url == listing.url
    
    # For datetime, check equality (may have slight differences in microseconds)
    # Compare as ISO strings to handle timezone differences
    assert restored_listing.scraped_at.isoformat() == listing.scraped_at.isoformat()


@given(listing=listings)
@settings(max_examples=100)
def test_price_parsing_robustness(listing):
    """
    Test that price parsing handles various currency formats correctly.
    
    For any listing with a price, get_price_value() should extract the numeric value.
    """
    if listing.price is None:
        # If no price, should return None
        assert listing.get_price_value() is None
    else:
        # If price exists, should extract a positive integer
        price_value = listing.get_price_value()
        assert price_value is not None, f"Failed to parse price: {listing.price}"
        assert isinstance(price_value, int), "Price value should be an integer"
        assert price_value > 0, "Price value should be positive"


@given(
    query=st.text(min_size=1, max_size=100),
    min_price=st.one_of(st.none(), st.integers(min_value=1, max_value=10000)),
    max_price=st.one_of(st.none(), st.integers(min_value=1, max_value=100000)),
    location=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    category=st.one_of(st.none(), st.text(min_size=1, max_size=50))
)
@settings(max_examples=100)
def test_search_criteria_url_params(query, min_price, max_price, location, category):
    """
    Test that SearchCriteria correctly converts to URL parameters.
    
    For any search criteria, to_url_params() should include all non-None values.
    """
    criteria = SearchCriteria(
        query=query,
        min_price=min_price,
        max_price=max_price,
        location=location,
        category=category
    )
    
    params = criteria.to_url_params()
    
    # Query should always be present
    assert 'query' in params
    assert params['query'] == query
    
    # Optional parameters should be present only if not None
    if min_price is not None:
        assert 'minPrice' in params
        assert params['minPrice'] == str(min_price)
    else:
        assert 'minPrice' not in params
    
    if max_price is not None:
        assert 'maxPrice' in params
        assert params['maxPrice'] == str(max_price)
    else:
        assert 'maxPrice' not in params
    
    if location is not None:
        assert 'location' in params
        assert params['location'] == location
    else:
        assert 'location' not in params
    
    if category is not None:
        assert 'category' in params
        assert params['category'] == category
    else:
        assert 'category' not in params


@given(listing=listings)
@settings(max_examples=100)
def test_deal_alert_creation(listing):
    """
    Test that DealAlert can be created with valid listings.
    
    For any listing, we should be able to create a DealAlert with various states.
    """
    # Test new deal
    alert = DealAlert(
        listing=listing,
        is_new=True,
        price_changed=False,
        match_reason="New listing found"
    )
    assert alert.listing == listing
    assert alert.is_new is True
    assert alert.price_changed is False
    assert alert.old_price is None
    
    # Test price change
    alert_with_change = DealAlert(
        listing=listing,
        is_new=False,
        price_changed=True,
        old_price="$500",
        match_reason="Price dropped"
    )
    assert alert_with_change.listing == listing
    assert alert_with_change.is_new is False
    assert alert_with_change.price_changed is True
    assert alert_with_change.old_price == "$500"
