"""
Main entry point and CLI for Marketplace Deal Scout.

Provides command-line interface for searching Facebook Marketplace deals
with support for query, price filters, and location parameters.
"""

import asyncio
import argparse
import logging
import sys
from typing import Optional
from datetime import datetime

from src.agent.sdk_agent import SDKDealScoutAgent
from src.config.agent_config import get_agent_settings, AGENT_CONFIG
from src.models import DealAlert


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_deal_alert(alert: DealAlert) -> str:
    """
    Format a deal alert for console output.
    
    Args:
        alert: DealAlert object to format
        
    Returns:
        Formatted string representation of the deal
    """
    listing = alert.listing
    
    # Build the output string
    lines = []
    
    # Title and ID
    title = listing.title or "[No title]"
    lines.append(f"📌 {title}")
    lines.append(f"   ID: {listing.id}")
    
    # Price information
    if listing.price:
        if alert.price_changed and alert.old_price:
            lines.append(f"   Price: {listing.price} (was {alert.old_price})")
        else:
            lines.append(f"   Price: {listing.price}")
    
    # Location
    if listing.location:
        lines.append(f"   Location: {listing.location}")
    
    # Image URL
    if listing.image_url:
        lines.append(f"   Image: {listing.image_url}")
    
    # URL
    lines.append(f"   URL: {listing.url}")
    
    # Deal status
    if alert.is_new:
        lines.append("   ✨ NEW DEAL")
    elif alert.price_changed:
        lines.append("   💰 PRICE CHANGED")
    
    if alert.match_reason:
        lines.append(f"   Reason: {alert.match_reason}")
    
    lines.append("")  # Blank line for spacing
    
    return "\n".join(lines)


def format_results(alerts: list) -> str:
    """
    Format a list of deal alerts for console output.
    
    Args:
        alerts: List of DealAlert objects
        
    Returns:
        Formatted string representation of all deals
    """
    if not alerts:
        return "No deals found matching your criteria.\n"
    
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"Found {len(alerts)} deal(s)")
    output.append(f"{'='*60}\n")
    
    new_deals = [a for a in alerts if a.is_new]
    price_changes = [a for a in alerts if a.price_changed and not a.is_new]
    
    if new_deals:
        output.append(f"✨ NEW DEALS ({len(new_deals)}):\n")
        for alert in new_deals:
            output.append(format_deal_alert(alert))
    
    if price_changes:
        output.append(f"💰 PRICE CHANGES ({len(price_changes)}):\n")
        for alert in price_changes:
            output.append(format_deal_alert(alert))
    
    output.append(f"{'='*60}\n")
    
    return "".join(output)


async def run_deal_scout(
    query: str,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    location: Optional[str] = None,
    verbose: bool = False
) -> int:
    """
    Execute the deal scout search workflow.
    
    Args:
        query: Search keywords
        max_price: Maximum price filter (optional)
        min_price: Minimum price filter (optional)
        location: Location filter (optional)
        verbose: Enable verbose logging output
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Set logging level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        logger.info("Initializing Marketplace Deal Scout...")
        
        # Get agent settings
        settings = get_agent_settings()
        logger.info(f"Using configuration: {AGENT_CONFIG}")
        
        # Initialize the SDK-compatible deal scout agent
        deal_scout = SDKDealScoutAgent(settings=settings)
        await deal_scout.initialize()
        
        logger.info("Deal Scout initialized successfully")
        
        # Validate inputs
        if not query or not query.strip():
            logger.error("Search query cannot be empty")
            print("Error: Search query is required", file=sys.stderr)
            return 1
        
        if min_price is not None and max_price is not None:
            if min_price > max_price:
                logger.error(f"Invalid price range: min_price ({min_price}) > max_price ({max_price})")
                print(
                    f"Error: Minimum price ({min_price}) cannot be greater than maximum price ({max_price})",
                    file=sys.stderr
                )
                return 1
        
        if min_price is not None and min_price < 0:
            logger.error(f"Invalid minimum price: {min_price}")
            print("Error: Minimum price cannot be negative", file=sys.stderr)
            return 1
        
        if max_price is not None and max_price < 0:
            logger.error(f"Invalid maximum price: {max_price}")
            print("Error: Maximum price cannot be negative", file=sys.stderr)
            return 1
        
        # Log search parameters
        logger.info(f"Search parameters:")
        logger.info(f"  Query: {query}")
        if min_price is not None:
            logger.info(f"  Min Price: ${min_price}")
        if max_price is not None:
            logger.info(f"  Max Price: ${max_price}")
        if location:
            logger.info(f"  Location: {location}")
        
        # Execute search
        print(f"\n🔍 Searching for '{query}'...")
        if min_price is not None or max_price is not None:
            price_range = f"${min_price or '0'}-${max_price or '∞'}"
            print(f"   Price range: {price_range}")
        if location:
            print(f"   Location: {location}")
        print()
        
        start_time = datetime.now()
        
        # Execute the search workflow
        alerts = await deal_scout.search_deals(
            query=query,
            max_price=max_price,
            min_price=min_price,
            location=location
        )
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        # Format and display results
        results_output = format_results(alerts)
        print(results_output)
        
        # Summary
        new_count = sum(1 for a in alerts if a.is_new)
        price_change_count = sum(1 for a in alerts if a.price_changed and not a.is_new)
        
        logger.info(f"Search completed in {elapsed_time:.2f} seconds")
        logger.info(f"Results: {new_count} new deals, {price_change_count} price changes")
        
        print(f"✅ Search completed in {elapsed_time:.2f} seconds")
        print(f"   New deals: {new_count}")
        print(f"   Price changes: {price_change_count}")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Search interrupted by user")
        print("\n\n⚠️  Search interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
        
    except Exception as e:
        logger.exception(f"Search failed with error: {str(e)}")
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        print("\nFor more details, check the logs above.", file=sys.stderr)
        return 1


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for CLI.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="deal-scout",
        description="Search Facebook Marketplace for deals matching your criteria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for vintage guitars
  python -m src.main "vintage guitar"
  
  # Search with price range
  python -m src.main "laptop" --min-price 500 --max-price 1000
  
  # Search with location filter
  python -m src.main "bicycle" --location "San Francisco, CA"
  
  # Search with all filters
  python -m src.main "camera" --min-price 100 --max-price 500 --location "NYC"
  
  # Enable verbose logging
  python -m src.main "furniture" --verbose
        """
    )
    
    # Positional argument: search query
    parser.add_argument(
        "query",
        help="Search keywords (e.g., 'vintage guitar', 'laptop', 'bicycle')"
    )
    
    # Optional arguments: price filters
    parser.add_argument(
        "--min-price",
        type=int,
        default=None,
        help="Minimum price filter (in dollars, e.g., 100)"
    )
    
    parser.add_argument(
        "--max-price",
        type=int,
        default=None,
        help="Maximum price filter (in dollars, e.g., 1000)"
    )
    
    # Optional argument: location filter
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Location filter (e.g., 'San Francisco, CA' or 'New York')"
    )
    
    # Optional argument: verbose logging
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging output"
    )
    
    return parser


def main() -> int:
    """
    Main entry point for the CLI application.
    
    Parses command-line arguments and executes the deal scout search.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Run the async search function
    try:
        exit_code = asyncio.run(
            run_deal_scout(
                query=args.query,
                max_price=args.max_price,
                min_price=args.min_price,
                location=args.location,
                verbose=args.verbose
            )
        )
        return exit_code
    except Exception as e:
        logger.exception(f"Unexpected error in main: {str(e)}")
        print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
