"""
Test script for Enhanced Planner Agent with Aggregator integration.

This script demonstrates the complete pipeline:
1. Enhanced Planner Agent retrieves news from multiple sources
2. Aggregator Agent clusters and organizes the results
3. Results are processed and displayed with summaries

Usage:
    python test_enhanced_planner_with_aggregator.py

Environment Variables Required:
    - GEMINI_API_KEY: For AI-powered summarization
    - SUPABASE_URL: Optional, for database integration
    - SUPABASE_KEY: Optional, for database integration
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Import the enhanced planner integration
from news_agent.integration.planner_aggregator import create_enhanced_planner, EnhancedPlannerAgent
from news_agent.aggregator import AggregatorConfig

# Load environment variables
load_dotenv()

def print_separator(title: str):
    """Print a formatted separator for better output readability."""
    print("\n" + "="*60)
    print(f" {title} ")
    print("="*60)

def print_cluster_summary(cluster_data: dict, index: int):
    """Print a formatted cluster summary."""
    print(f"\n--- Cluster {index + 1}: {cluster_data['title']} ---")
    print(f"Sources: {cluster_data['metadata']['source_count']}")
    if cluster_data['metadata']['ticker']:
        print(f"Primary Ticker: {cluster_data['metadata']['ticker']}")
    if cluster_data['metadata']['topics']:
        print(f"Topics: {', '.join(cluster_data['metadata']['topics'])}")
    print(f"Confidence: {cluster_data['metadata']['confidence']:.2f}")

    print(f"\nSummary:")
    print(cluster_data['summary'])

    if cluster_data['key_points']:
        print(f"\nKey Points:")
        for i, point in enumerate(cluster_data['key_points'], 1):
            print(f"  {i}. {point}")

    print(f"\nSource URLs:")
    for i, source in enumerate(cluster_data['sources'][:3], 1):  # Show first 3 sources
        print(f"  {i}. {source.get('url', 'No URL')}")
    if len(cluster_data['sources']) > 3:
        print(f"  ... and {len(cluster_data['sources']) - 3} more sources")

def print_basic_results(results: dict):
    """Print basic planner results without aggregation."""
    print_separator("BASIC PLANNER RESULTS")

    print(f"Retriever Summary:")
    summary = results.get('retriever_summary', {})
    print(f"  Total Retrievers: {summary.get('total_retrievers', 0)}")
    print(f"  Successful: {summary.get('successful_retrievers', 0)}")
    print(f"  Failed: {summary.get('failed_retrievers', 0)}")
    print(f"  Total Articles: {summary.get('total_articles', 0)}")

    categories = ['breaking_news', 'financial_news', 'sec_filings', 'general_news']
    for category in categories:
        articles = results.get(category, [])
        print(f"\n{category.replace('_', ' ').title()}: {len(articles)} articles")
        for i, article in enumerate(articles[:2], 1):  # Show first 2 articles
            title = article.get('title', 'No title')[:80]
            print(f"  {i}. {title}...")
        if len(articles) > 2:
            print(f"  ... and {len(articles) - 2} more articles")

def print_enhanced_results(results: dict):
    """Print enhanced results with aggregation."""
    print_separator("ENHANCED RESULTS WITH AGGREGATION")

    # Processing stats
    processing_stats = results.get('processing_stats', {})
    print(f"Query: {processing_stats.get('query', 'Unknown')}")
    print(f"Retrieval Time: {processing_stats.get('retrieval_time', 0):.2f}s")
    print(f"Total Time: {processing_stats.get('total_time', 0):.2f}s")
    print(f"Aggregation Enabled: {processing_stats.get('aggregation_enabled', False)}")

    # Aggregation stats
    aggregation = results.get('aggregation', {})
    if aggregation.get('enabled'):
        print(f"\nAggregation Results:")
        print(f"  Clusters Found: {aggregation.get('cluster_count', 0)}")
        print(f"  Total Sources: {aggregation.get('total_sources', 0)}")

        # Cluster summaries
        summaries = results.get('summaries', [])
        if summaries:
            print_separator("CLUSTER SUMMARIES")
            for i, cluster in enumerate(summaries):
                print_cluster_summary(cluster, i)
        else:
            print("\nNo cluster summaries generated.")
    else:
        print(f"\nAggregation: Disabled or failed")
        if 'error' in aggregation.get('stats', {}):
            print(f"  Error: {aggregation['stats']['error']}")

def save_results_to_file(results: dict, filename: str):
    """Save results to JSON file for later analysis."""
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {filename}")
    except Exception as e:
        print(f"\nError saving results: {e}")

async def test_enhanced_planner_async():
    """Test the enhanced planner with aggregation in async mode."""
    print_separator("ASYNC ENHANCED PLANNER TEST")

    # Configuration
    query = "Amazon quarterly earnings AWS cloud revenue"
    user_preferences = {
        'watchlist': ['TSLA', 'AAPL', 'GOOGL'],
        'topics': ['technology', 'automotive', 'artificial_intelligence'],
        'keywords': ['autonomous', 'electric', 'innovation', 'earnings']
    }

    try:
        # Create enhanced planner with aggregation
        planner = create_enhanced_planner(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            max_retrievers=5,
            config_overrides={
                'clustering': {
                    'min_cluster_size': 2,
                    'similarity_threshold': 0.65
                },
                'summarization': {
                    'max_tokens': 200,
                    'temperature': 0.3
                }
            }
        )

        print(f"Enhanced Planner Summary:")
        # No direct get_planner_summary on EnhancedPlannerAgent, access through planner_agent
        # For now, we'll just print a placeholder or remove this section if not directly available
        # print(f"  Aggregation Enabled: {planner.enable_aggregation}")
        # print(f"  Has Aggregator: {planner.aggregator is not None}")
        # print(f"  Max Concurrent Retrievers: {planner.planner_agent.max_concurrent_retrievers}")

        print(f"\nRunning query: '{query}'")
        print(f"User preferences: {user_preferences}")

        # Run enhanced search with aggregation
        start_time = datetime.now()
        results = await planner.run_async(
            query=query,
            user_preferences=user_preferences,
            return_aggregated=True
        )
        end_time = datetime.now()

        print(f"\nSearch completed in {(end_time - start_time).total_seconds():.2f} seconds")

        # Display results
        if results:
            for result in results:
                print_enhanced_results(result)
        else:
            print("\nNo results returned from async enhanced planner test.")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_planner_results_{timestamp}.json"
        save_results_to_file(results, filename)

        # Cleanup
        planner.cleanup()

        return results

    except Exception as e:
        print(f"Async test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_enhanced_planner_sync():
    """Test the enhanced planner with aggregation in sync mode."""
    print_separator("SYNC ENHANCED PLANNER TEST")

    query = "Microsoft AI announcement cloud computing"
    user_preferences = {
        'watchlist': ['MSFT', 'NVDA', 'AMZN'],
        'topics': ['artificial_intelligence', 'cloud_computing', 'enterprise'],
        'keywords': ['GPT', 'Azure', 'OpenAI', 'earnings']
    }

    try:
        # Create enhanced planner with different config
        planner = create_enhanced_planner(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            max_retrievers=3,
            config_overrides={
                'clustering': {
                    'min_cluster_size': 2, # Changed from 1 to 2
                    'similarity_threshold': 0.7
                }
            }
        )

        print(f"Running query: '{query}'")

        # Run synchronous search
        start_time = datetime.now()
        results = planner.run(
            query=query,
            user_preferences=user_preferences,
            return_aggregated=True
        )
        end_time = datetime.now()

        print(f"\nSync search completed in {(end_time - start_time).total_seconds():.2f} seconds")

        # Display results
        if results and isinstance(results, list) and len(results) > 0:
            # Sync run returns a list of dictionaries, process the first one for display
            print_enhanced_results(results[0])
        else:
            print("\nNo results returned from sync enhanced planner test.")

        # Cleanup
        planner.cleanup()

        return results

    except Exception as e:
        print(f"Sync test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_fallback_mode():
    """Test enhanced planner in fallback mode (no aggregation)."""
    print_separator("FALLBACK MODE TEST (NO AGGREGATION)")

    query = "Apple iPhone new features 2024"

    try:
        # Create planner without aggregation
        from news_agent.integration.planner_aggregator import create_basic_planner
        planner = create_basic_planner(max_retrievers=3)

        print(f"Running query: '{query}' (aggregation disabled)")

        # Run search without aggregation
        start_time = datetime.now()
        results = planner.run(query=query, return_aggregated=False)
        end_time = datetime.now()

        print(f"\nFallback search completed in {(end_time - start_time).total_seconds():.2f} seconds")

        # Display basic results
        if results and isinstance(results, list) and len(results) > 0:
            # Fallback mode returns a list of dictionaries, process the first one for display
            print_basic_results(results[0])
        else:
            print("\nNo results returned from fallback mode test.")

        return results

    except Exception as e:
        print(f"Fallback test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_modes():
    """Compare results from different modes."""
    print_separator("COMPARISON TEST")

    query = "Amazon quarterly earnings AWS cloud revenue"

    try:
        # Test with aggregation
        print("\n1. Testing WITH aggregation:")
        planner_with_agg = create_enhanced_planner(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            max_retrievers=3
        )

        start_time = datetime.now()
        results_with_agg = planner_with_agg.run(query=query, return_aggregated=True)
        time_with_agg = (datetime.now() - start_time).total_seconds()

        print(f"  Time: {time_with_agg:.2f}s")
        # results_with_agg is a list of dicts, so we need to iterate or access the first element
        if results_with_agg and isinstance(results_with_agg, list) and len(results_with_agg) > 0:
            first_result = results_with_agg[0]
            print(f"  Clusters: {len(first_result.get('summaries', []))}")
            print(f"  Total Sources: {first_result.get('aggregation', {}).get('total_sources', 0)}")
        else:
            print("  No aggregated results for comparison.")

        planner_with_agg.cleanup()

        # Test without aggregation
        print("\n2. Testing WITHOUT aggregation:")
        from news_agent.integration.planner_aggregator import create_basic_planner
        planner_without_agg = create_basic_planner(max_retrievers=3)

        start_time = datetime.now()
        results_without_agg = planner_without_agg.run(query=query, return_aggregated=False)
        time_without_agg = (datetime.now() - start_time).total_seconds()

        # results_without_agg is a list of dicts, so we need to access the first element
        if results_without_agg and isinstance(results_without_agg, list) and len(results_without_agg) > 0:
            first_result_without_agg = results_without_agg[0]
            summary = first_result_without_agg.get('retriever_summary', {})
            print(f"  Time: {time_without_agg:.2f}s")
            print(f"  Total Articles: {summary.get('total_articles', 0)}")
            print(f"  Successful Retrievers: {summary.get('successful_retrievers', 0)}")
        else:
            print("  No non-aggregated results for comparison.")

        # Comparison summary
        print(f"\nComparison Summary:")
        print(f"  Aggregation overhead: +{time_with_agg - time_without_agg:.2f}s")
        if results_with_agg and isinstance(results_with_agg, list) and len(results_with_agg) > 0:
            first_result_agg = results_with_agg[0]
            print(f"  Value added: {len(first_result_agg.get('summaries', []))} organized clusters")
        else:
            print("  No aggregated results for value added comparison.")

        return results_with_agg, results_without_agg

    except Exception as e:
        print(f"Comparison test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def main():
    """Main test function."""
    print_separator("ENHANCED PLANNER + AGGREGATOR TEST SUITE")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Check environment
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("WARNING: GEMINI_API_KEY not found in environment")
        print("Some features may not work properly")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not (supabase_url and supabase_key):
        print("INFO: Supabase credentials not found - running without database integration")

    # Run tests
    try:
        # Test 1: Async mode with full aggregation
        await test_enhanced_planner_async()

        # Test 2: Sync mode with aggregation
        test_enhanced_planner_sync()

        # Test 3: Fallback mode without aggregation
        test_fallback_mode()

        # Test 4: Compare modes
        compare_modes()

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