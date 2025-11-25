"""
Property-based tests for extraction engine.

These tests verify universal properties that should hold for listing extraction,
ID extraction, and price parsing operations.
"""

import pytest
from hypothesis import given, settings, strategies as st
import re

from src.extraction_engine import ListingExtractor


# Strategy for generating marketplace URLs with valid IDs
def marketplace_url_with_id(id_str):
    """Generate a marketplace URL with the given ID."""
    return f"https://www.facebook.com/marketplace/item/{id_str}/"


# Strategy for valid listing IDs (numeric strings)
listing_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)),
    min_size=10,
    max_size=20
)

# Strategy for marketplace URLs
marketplace_urls = st.builds(
    marketplace_url_with_id,
    listing_ids
)

# Strategy for price strings with various currency symbols
price_strings = st.one_of(
    # Dollar prices
    st.builds(
        lambda val: f"${val:,}",
        st.integers(min_value=1, max_value=100000)
    ),
    # Euro prices
    st.builds(
        lambda val: f"€{val:,}",
        st.integers(min_value=1, max_value=100000)
    ),
    # Pound prices
    st.builds(
        lambda val: f"£{val:,}",
        st.integers(min_value=1, max_value=100000)
    ),
    # Prices with spaces after currency
    st.builds(
        lambda val: f"$ {val:,}",
        st.integers(min_value=1, max_value=100000)
    ),
    # Prices without commas
    st.builds(
        lambda val: f"${val}",
        st.integers(min_value=1, max_value=999)
    )
)


@given(url=marketplace_urls)
@settings(max_examples=100)
def test_id_extraction_correctness(url):
    """
    **Feature: marketplace-deal-scout, Property 9: ID extraction correctness**
    
    For any marketplace item URL matching the pattern /marketplace/item/{ID}/,
    the extracted ID should equal the numeric value from the URL.
    
    **Validates: Requirements 2.3**
    """
    # Extract the expected ID from the URL using the same pattern
    expected_match = re.search(r'/marketplace/item/(\d+)', url)
    assert expected_match is not None, f"Test URL should match pattern: {url}"
    expected_id = expected_match.group(1)
    
    # Use the extractor to get the ID
    extracted_id = ListingExtractor.extract_id_from_url(url)
    
    # Verify the extracted ID matches the expected ID
    assert extracted_id is not None, f"Failed to extract ID from URL: {url}"
    assert extracted_id == expected_id, \
        f"Extracted ID '{extracted_id}' doesn't match expected '{expected_id}'"


@given(price_str=price_strings)
@settings(max_examples=100)
def test_price_parsing_robustness(price_str):
    """
    **Feature: marketplace-deal-scout, Property 11: Price parsing robustness**
    
    For any price string containing currency symbols ($, €, £) and numeric values
    with optional commas, the parser should extract the numeric value correctly.
    
    **Validates: Requirements 2.5, 9.4**
    """
    # Parse the price
    parsed_value = ListingExtractor.parse_price_string(price_str)
    
    # Should successfully extract a value
    assert parsed_value is not None, f"Failed to parse price: {price_str}"
    assert isinstance(parsed_value, int), "Parsed price should be an integer"
    assert parsed_value > 0, "Parsed price should be positive"
    
    # Verify the parsed value matches the numeric content
    # Extract just the digits from the original string
    digits_only = re.sub(r'[^\d]', '', price_str)
    expected_value = int(digits_only)
    
    assert parsed_value == expected_value, \
        f"Parsed value {parsed_value} doesn't match expected {expected_value} from '{price_str}'"


@given(listings_data=st.lists(
    st.builds(
        lambda id, title, price: {
            'id': id,
            'title': title,
            'price': price,
            'location': None,
            'imageUrl': None,
            'url': f"https://www.facebook.com/marketplace/item/{id}/",
            'scrapedAt': 1700000000000
        },
        id=listing_ids,
        title=st.one_of(st.none(), st.text(min_size=10, max_size=100)),
        price=st.one_of(st.none(), price_strings)
    ).filter(lambda item: item['title'] is not None or item['price'] is not None),
    min_size=1,
    max_size=50
))
@settings(max_examples=100)
def test_unique_listing_ids(listings_data):
    """
    **Feature: marketplace-deal-scout, Property 10: Unique listing IDs**
    
    For any extraction result set, no two listings should have the same listing ID.
    
    **Validates: Requirements 2.4**
    """
    import json
    
    # Create an extractor
    extractor = ListingExtractor()
    
    # Convert listings data to JSON string (simulating extraction output)
    json_str = json.dumps(listings_data)
    
    # Parse the results
    listings = extractor._parse_extraction_results(json_str)
    
    # Collect all IDs
    listing_ids_found = [listing.id for listing in listings]
    
    # Verify all IDs are unique
    unique_ids = set(listing_ids_found)
    assert len(listing_ids_found) == len(unique_ids), \
        f"Found duplicate listing IDs: {len(listing_ids_found)} total, {len(unique_ids)} unique"
    
    # Verify each listing has a non-null ID
    for listing in listings:
        assert listing.id is not None, "All listings must have non-null IDs"
        assert len(listing.id) > 0, "All listing IDs must be non-empty"


# Additional edge case tests for robustness

@given(url=st.text())
@settings(max_examples=100)
def test_id_extraction_handles_invalid_urls(url):
    """
    Test that ID extraction returns None for invalid URLs.
    
    For any string that doesn't match the marketplace URL pattern,
    extraction should return None rather than raising an error.
    """
    # Filter out valid marketplace URLs for this test
    if '/marketplace/item/' in url and re.search(r'/marketplace/item/(\d+)', url):
        return  # Skip valid URLs
    
    # Should return None for invalid URLs
    result = ListingExtractor.extract_id_from_url(url)
    assert result is None, f"Should return None for invalid URL: {url}"


@given(price_str=st.text())
@settings(max_examples=100)
def test_price_parsing_handles_invalid_strings(price_str):
    """
    Test that price parsing returns None for strings without valid prices.
    
    For any string that doesn't contain a valid price pattern,
    parsing should return None rather than raising an error.
    """
    # Filter out valid price strings for this test
    if re.search(r'[\$€£]?\s*\d', price_str):
        return  # Skip strings that might contain valid prices
    
    # Should return None for invalid price strings
    result = ListingExtractor.parse_price_string(price_str)
    assert result is None, f"Should return None for invalid price string: {price_str}"
