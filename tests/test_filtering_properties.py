"""
Property-based tests for listing filtering.

These tests verify universal properties that should hold across all valid
executions of the filtering operations.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume
from datetime import datetime
from src.models import Listing
from src.filtering import ListingFilter


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

# Strategy for generating datetimes
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


@given(
    listings_list=st.lists(listings, min_size=0, max_size=50),
    max_price=st.integers(min_value=1, max_value=100000)
)
@settings(max_examples=100)
def test_maximum_price_filtering(listings_list, max_price):
    """
    **Feature: marketplace-deal-scout, Property 27: Maximum price filtering**
    
    For any set of listings and maximum price M, all filtered results should 
    have prices ≤ M.
    
    **Validates: Requirements 9.1**
    """
    filter_obj = ListingFilter()
    
    # Filter by maximum price only
    filtered = filter_obj.filter_by_price(listings_list, max_price=max_price)
    
    # All filtered listings must have prices <= max_price
    for listing in filtered:
        price_value = listing.get_price_value()
        assert price_value is not None, "Filtered listing should have extractable price"
        assert price_value <= max_price, \
            f"Listing price {price_value} exceeds maximum {max_price}"


@given(
    listings_list=st.lists(listings, min_size=0, max_size=50),
    min_price=st.integers(min_value=1, max_value=50000),
    max_price=st.integers(min_value=1, max_value=100000)
)
@settings(max_examples=100)
def test_price_range_filtering(listings_list, min_price, max_price):
    """
    **Feature: marketplace-deal-scout, Property 28: Price range filtering**
    
    For any set of listings with minimum price MIN and maximum price MAX, 
    all filtered results should have prices where MIN ≤ price ≤ MAX.
    
    **Validates: Requirements 9.2**
    """
    # Ensure min_price <= max_price for valid range
    assume(min_price <= max_price)
    
    filter_obj = ListingFilter()
    
    # Filter by price range
    filtered = filter_obj.filter_by_price(
        listings_list, 
        min_price=min_price, 
        max_price=max_price
    )
    
    # All filtered listings must have prices within the range
    for listing in filtered:
        price_value = listing.get_price_value()
        assert price_value is not None, "Filtered listing should have extractable price"
        assert min_price <= price_value <= max_price, \
            f"Listing price {price_value} outside range [{min_price}, {max_price}]"


@given(
    listings_list=st.lists(listings, min_size=0, max_size=50),
    min_price=st.one_of(st.none(), st.integers(min_value=1, max_value=50000)),
    max_price=st.one_of(st.none(), st.integers(min_value=1, max_value=100000))
)
@settings(max_examples=100)
def test_missing_price_exclusion(listings_list, min_price, max_price):
    """
    **Feature: marketplace-deal-scout, Property 29: Missing price exclusion**
    
    For any price filtering operation, listings without extractable prices 
    should not appear in the filtered results.
    
    **Validates: Requirements 9.3**
    """
    # Skip if min_price > max_price (invalid range)
    if min_price is not None and max_price is not None:
        assume(min_price <= max_price)
    
    filter_obj = ListingFilter()
    
    # Filter by price (with or without range)
    filtered = filter_obj.filter_by_price(
        listings_list,
        min_price=min_price,
        max_price=max_price
    )
    
    # All filtered listings must have extractable prices
    for listing in filtered:
        price_value = listing.get_price_value()
        assert price_value is not None, \
            f"Filtered listing should have extractable price, but got None for: {listing.price}"
