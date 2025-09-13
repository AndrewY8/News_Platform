"""
Test script for Basic Planner Agent only (no aggregation).

This script tests just the planner retrieval functionality without aggregation.
Useful for testing when aggregator dependencies are missing.
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Import just the basic planner
from news_agent.agent import PlannerAgent

# Load environment variables
load_dotenv()

def print_separator(title: str):
    """Print a formatted separator for better output readability."""
    print("\n" + "="*60)
    print(f" {title} ")
    print("="*60)

def print_results(results: dict):
    """Print planner results."""
    print_separator("PLANNER RESULTS")

    print(f"Retriever Summary:")
    summary = results.get('retriever_summary', {})
    print(f"  Total Retrievers: {summary.get('total_retrievers', 0)}")
    print(f"  Successful: {summary.get('successful_retrievers', 0)}")
    print(f"  Failed: {summary.get('failed_retrievers', 0)}")
    print(f"  Total Articles: {summary.get('total_articles', 0)}")

    # Show errors if any
    errors = results.get('errors', [])
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  - {error.get('retriever', 'Unknown')}: {error.get('error', 'Unknown error')}")

    categories = ['breaking_news', 'financial_news', 'sec_filings', 'general_news']
    for category in categories:
        articles = results.get(category, [])
        print(f"\n{category.replace('_', ' ').title()}: {len(articles)} articles")
        for i, article in enumerate(articles[:3], 1):  # Show first 3 articles
            title = article.get('title', 'No title')[:80]
            url = article.get('url', 'No URL')[:50]
            print(f"  {i}. {title}...")
            print(f"     URL: {url}...")
        if len(articles) > 3:
            print(f"  ... and {len(articles) - 3} more articles")

async def test_basic_planner_async():
    """Test basic planner in async mode."""
    print_separator("ASYNC BASIC PLANNER TEST")

    query = "Tesla autonomous driving latest news"

    try:
        # Create basic planner
        planner = PlannerAgent(max_concurrent_retrievers=3)

        print(f"Running query: '{query}'")

        # Run async search
        start_time = datetime.now()
        results = await planner.run_async(query)
        end_time = datetime.now()

        print(f"\nAsync search completed in {(end_time - start_time).total_seconds():.2f} seconds")

        # Display results
        # print("HERE" , results)
        print_results(results)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"basic_planner_results_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {filename}")

        return results

    except Exception as e:
        print(f"Async test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_basic_planner_sync():
    """Test basic planner in sync mode."""
    print_separator("SYNC BASIC PLANNER TEST")

    query = "Microsoft AI developments"

    try:
        # Create basic planner
        planner = PlannerAgent(max_concurrent_retrievers=3)

        print(f"Running query: '{query}'")

        # Run sync search
        start_time = datetime.now()
        results = planner.run(query)
        end_time = datetime.now()

        print(f"\nSync search completed in {(end_time - start_time).total_seconds():.2f} seconds")

        # Display results
        print(results)
        with open(f"basic_planner_agent_test_{datetime.now().isoformat()}.json", 'w') as json_file:
            json.dump(results, json_file)
        # print_results(results)

        return results

    except Exception as e:
        print(f"Sync test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main test function."""
    print_separator("BASIC PLANNER TEST SUITE")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Check environment - show what retrievers are available
    print("\nEnvironment Check:")
    api_keys = [
        ('TAVILY_API_KEY', 'Tavily Search'),
        ('GOOGLE_API_KEY', 'Google Search'),
        ('SERPER_API_KEY', 'Serper Search'),
        ('SEARCHAPI_API_KEY', 'SearchAPI'),
        ('EXA_API_KEY', 'Exa Search'),
        ('SERPAPI_API_KEY', 'SerpAPI'),
    ]

    available_count = 0
    for env_var, name in api_keys:
        value = os.getenv(env_var)
        if value:
            print(f"  ✓ {name}: Available")
            available_count += 1
        else:
            print(f"  ✗ {name}: Missing")

    print(f"\nTotal available retrievers: {available_count}")

    if available_count == 0:
        print("WARNING: No API keys found. Some retrievers may not work.")

    # Run tests
    try:
        # Test 1: Async mode
        # await test_basic_planner_async()

        # Test 2: Sync mode
        test_basic_planner_sync()

        print_separator("ALL TESTS COMPLETED")

    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())