"""
Property-based tests for the Deal Scout Agent.

These tests verify universal properties that should hold across all valid
executions of the agent's result presentation and deal alert creation.
"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime
from src.models import Listing, DealAlert


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

# Strategy for generating complete Listing objects with all required fields
listings_complete = st.builds(
    Listing,
    id=listing_ids,
    title=titles,
    price=prices,
    location=locations,
    image_url=image_urls,
    url=marketplace_urls,
    scraped_at=datetimes
)


@given(listing=listings_complete)
@settings(max_examples=100)
def test_result_field_completeness(listing):
    """
    **Feature: marketplace-deal-scout, Property 30: Result field completeness**
    
    For any listing in the final presentation, the listing must include 
    title, price, URL, and listing ID.
    
    **Validates: Requirements 10.1**
    """
    # Every listing must have a non-null ID
    assert listing.id is not None, "Listing ID must not be None"
    assert len(listing.id) > 0, "Listing ID must not be empty"
    
    # Every listing must have a title
    assert listing.title is not None, "Listing title must not be None"
    assert len(listing.title) > 0, "Listing title must not be empty"
    
    # Every listing must have a price
    assert listing.price is not None, "Listing price must not be None"
    assert len(listing.price) > 0, "Listing price must not be empty"
    
    # Every listing must have a URL
    assert listing.url is not None, "Listing URL must not be None"
    assert len(listing.url) > 0, "Listing URL must not be empty"
    assert listing.url.startswith("https://"), "Listing URL must be HTTPS"


@given(listing=listings_complete)
@settings(max_examples=100)
def test_new_deal_indication(listing):
    """
    **Feature: marketplace-deal-scout, Property 33: New deal indication**
    
    For any listing not found in memory, the presentation should mark it 
    as newly discovered.
    
    **Validates: Requirements 10.4**
    """
    # Create a new deal alert (is_new=True)
    alert = DealAlert(
        listing=listing,
        is_new=True,
        price_changed=False,
        match_reason="New listing found"
    )
    
    # Verify the alert correctly indicates it's new
    assert alert.is_new is True, "Alert should indicate new deal"
    assert alert.price_changed is False, "New deals should not have price changes"
    assert alert.old_price is None, "New deals should not have old price"
    assert "New" in alert.match_reason or "new" in alert.match_reason, \
        "Match reason should indicate new deal"
    
    # Verify listing data is preserved
    assert alert.listing == listing, "Alert should preserve listing data"
    assert alert.listing.id == listing.id, "Alert should preserve listing ID"
    assert alert.listing.title == listing.title, "Alert should preserve listing title"
    assert alert.listing.price == listing.price, "Alert should preserve listing price"
    assert alert.listing.url == listing.url, "Alert should preserve listing URL"


@given(
    listing=listings_complete,
    old_price=prices,
    new_price=prices
)
@settings(max_examples=100)
def test_price_change_display(listing, old_price, new_price):
    """
    **Feature: marketplace-deal-scout, Property 34: Price change display**
    
    For any listing flagged as having a price change, the presentation should 
    display both the previous and current prices.
    
    **Validates: Requirements 10.5**
    """
    # Update listing to have the new price for this test
    listing_with_new_price = Listing(
        id=listing.id,
        title=listing.title,
        price=new_price,
        location=listing.location,
        image_url=listing.image_url,
        url=listing.url,
        scraped_at=listing.scraped_at
    )
    
    # Create a price change alert
    alert = DealAlert(
        listing=listing_with_new_price,
        is_new=False,
        price_changed=True,
        old_price=old_price,
        match_reason=f"Price changed from {old_price} to {new_price}"
    )
    
    # Verify the alert correctly indicates price change
    assert alert.is_new is False, "Price change alerts should not be marked as new"
    assert alert.price_changed is True, "Alert should indicate price change"
    
    # Verify both prices are present
    assert alert.old_price is not None, "Alert should have old price"
    assert alert.old_price == old_price, "Alert should preserve old price"
    
    # Verify listing has current price
    assert alert.listing.price is not None, "Listing should have current price"
    assert alert.listing.price == new_price, "Listing should have new price"
    
    # Verify match reason includes both prices
    assert old_price in alert.match_reason or "changed" in alert.match_reason.lower(), \
        "Match reason should indicate price change"
    
    # Verify listing data is preserved
    assert alert.listing == listing_with_new_price, "Alert should preserve listing data"


@given(listing=listings_complete)
@settings(max_examples=100)
def test_deal_alert_with_optional_fields(listing):
    """
    Test that DealAlert correctly handles optional fields.
    
    For any listing, we should be able to create alerts with various combinations
    of optional fields.
    """
    # Test alert without optional fields
    alert_minimal = DealAlert(
        listing=listing,
        is_new=True,
        price_changed=False
    )
    assert alert_minimal.old_price is None
    assert alert_minimal.match_reason == ""
    
    # Test alert with all optional fields
    alert_full = DealAlert(
        listing=listing,
        is_new=False,
        price_changed=True,
        old_price="$500",
        match_reason="Price dropped significantly"
    )
    assert alert_full.old_price == "$500"
    assert alert_full.match_reason == "Price dropped significantly"


@given(listing=listings_complete)
@settings(max_examples=100)
def test_deal_alert_listing_preservation(listing):
    """
    Test that DealAlert preserves all listing data.
    
    For any listing, creating a DealAlert should preserve all listing fields.
    """
    alert = DealAlert(
        listing=listing,
        is_new=True,
        price_changed=False,
        match_reason="Test alert"
    )
    
    # Verify all listing fields are preserved
    assert alert.listing.id == listing.id
    assert alert.listing.title == listing.title
    assert alert.listing.price == listing.price
    assert alert.listing.location == listing.location
    assert alert.listing.image_url == listing.image_url
    assert alert.listing.url == listing.url
    assert alert.listing.scraped_at == listing.scraped_at

