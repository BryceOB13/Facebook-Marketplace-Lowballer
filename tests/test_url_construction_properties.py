"""
Property-based tests for URL construction.

These tests verify universal properties that should hold for all URL
construction operations across randomly generated inputs.
"""

import pytest
from hypothesis import given, settings, strategies as st
from urllib.parse import urlparse, parse_qs, unquote_plus
import re
from src.url_builder import MarketplaceURLBuilder
from src.models import SearchCriteria


# Strategy for generating search queries with various characters
# Exclude control characters and other problematic characters that wouldn't
# appear in realistic search queries
search_queries = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'Z'),  # Letters, Numbers, Separators (spaces)
        min_codepoint=32,  # Start from space character
        max_codepoint=126  # ASCII printable characters
    ) | st.sampled_from(['-', '_', '.', '!', '@', '#', '&', '(', ')', '+', '=']),
    min_size=1,
    max_size=100
)

# Strategy for generating prices
prices = st.integers(min_value=1, max_value=100000)

# Strategy for generating locations
locations = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'Z')),
    min_size=1,
    max_size=50
)


@given(query=search_queries)
@settings(max_examples=100)
def test_valid_url_encoding(query):
    """
    **Feature: marketplace-deal-scout, Property 1: Valid URL encoding**
    
    For any search query string, the constructed marketplace URL should contain 
    properly URL-encoded query parameters with no unencoded special characters.
    
    **Validates: Requirements 1.1**
    """
    builder = MarketplaceURLBuilder()
    url = builder.build_search_url(query)
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Verify base URL structure
    assert parsed.scheme == "https", "URL should use HTTPS"
    assert parsed.netloc == "www.facebook.com", "URL should be for facebook.com"
    assert parsed.path == "/marketplace/search", "URL should be for marketplace search"
    
    # Verify query string exists
    assert parsed.query, "URL should have query parameters"
    
    # Parse query parameters
    params = parse_qs(parsed.query)
    
    # Verify query parameter exists
    assert 'query' in params, "URL should contain 'query' parameter"
    
    # Decode and verify the query matches original
    # Note: + in URLs represents space, so we normalize both for comparison
    decoded_query = unquote_plus(params['query'][0])
    normalized_original = query.replace('+', ' ')
    assert decoded_query == normalized_original, \
        f"Decoded query should match original: {decoded_query} != {normalized_original}"
    
    # Verify no unencoded special characters in the query string
    # The query string should only contain safe URL characters
    # Safe characters: A-Z a-z 0-9 - _ . ~ (unreserved) + & = % (reserved/encoded)
    safe_pattern = re.compile(r'^[A-Za-z0-9\-_.~+&=%]*$')
    assert safe_pattern.match(parsed.query), \
        f"Query string contains unencoded special characters: {parsed.query}"


@given(
    query=search_queries,
    min_price=st.one_of(st.none(), prices),
    max_price=st.one_of(st.none(), prices)
)
@settings(max_examples=100)
def test_price_filter_inclusion(query, min_price, max_price):
    """
    **Feature: marketplace-deal-scout, Property 2: Price filter inclusion**
    
    For any combination of min_price and max_price values, the constructed URL 
    should include both minPrice and maxPrice parameters in the query string when provided.
    
    **Validates: Requirements 1.3**
    """
    builder = MarketplaceURLBuilder()
    url = builder.build_search_url(query, min_price=min_price, max_price=max_price)
    
    # Parse the URL
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    # Verify minPrice parameter inclusion
    if min_price is not None:
        assert 'minPrice' in params, "URL should contain 'minPrice' when min_price is provided"
        assert params['minPrice'][0] == str(min_price), \
            f"minPrice parameter should match provided value: {params['minPrice'][0]} != {min_price}"
    else:
        assert 'minPrice' not in params, "URL should not contain 'minPrice' when min_price is None"
    
    # Verify maxPrice parameter inclusion
    if max_price is not None:
        assert 'maxPrice' in params, "URL should contain 'maxPrice' when max_price is provided"
        assert params['maxPrice'][0] == str(max_price), \
            f"maxPrice parameter should match provided value: {params['maxPrice'][0]} != {max_price}"
    else:
        assert 'maxPrice' not in params, "URL should not contain 'maxPrice' when max_price is None"


@given(
    query=search_queries,
    location=st.one_of(st.none(), locations)
)
@settings(max_examples=100)
def test_optional_parameter_handling(query, location):
    """
    **Feature: marketplace-deal-scout, Property 3: Optional parameter handling**
    
    For any optional location parameter, when provided, the constructed URL should 
    include the location parameter, and when not provided, the URL should not 
    contain location parameters.
    
    **Validates: Requirements 1.4**
    """
    builder = MarketplaceURLBuilder()
    url = builder.build_search_url(query, location=location)
    
    # Parse the URL
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    # Verify location parameter handling
    if location is not None and location != "":
        assert 'location' in params, "URL should contain 'location' when location is provided"
        decoded_location = unquote_plus(params['location'][0])
        assert decoded_location == location, \
            f"location parameter should match provided value: {decoded_location} != {location}"
    else:
        assert 'location' not in params, "URL should not contain 'location' when location is None or empty"


@given(
    query=search_queries,
    min_price=st.one_of(st.none(), prices),
    max_price=st.one_of(st.none(), prices),
    location=st.one_of(st.none(), locations),
    category=st.one_of(st.none(), st.text(min_size=1, max_size=50))
)
@settings(max_examples=100)
def test_build_from_criteria(query, min_price, max_price, location, category):
    """
    Test that build_from_criteria produces the same URL as build_search_url.
    
    For any SearchCriteria object, build_from_criteria should produce a URL
    equivalent to calling build_search_url with the same parameters.
    """
    builder = MarketplaceURLBuilder()
    
    criteria = SearchCriteria(
        query=query,
        min_price=min_price,
        max_price=max_price,
        location=location,
        category=category
    )
    
    # Build URL from criteria
    url_from_criteria = builder.build_from_criteria(criteria)
    
    # Build URL directly
    url_direct = builder.build_search_url(
        query=query,
        min_price=min_price,
        max_price=max_price,
        location=location
    )
    
    # Both should produce the same URL
    assert url_from_criteria == url_direct, \
        "build_from_criteria should produce same URL as build_search_url"
