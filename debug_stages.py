#!/usr/bin/env python3
"""
Debug the specific stages of the enhanced pipeline to see where articles are lost.
"""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, '/home/patrick/Documents/News_Platform')

load_dotenv()

async def debug_pipeline_stages():
    """Debug each stage step by step."""
    print("Debugging pipeline stages...")

    try:
        from enhanced_news_pipeline import create_enhanced_news_pipeline

        # Initialize pipeline
        pipeline = create_enhanced_news_pipeline(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            max_retrievers=3
        )

        query = "Nvidia recent news with US government"
        user_prefs = {
            'watchlist': ['NVDA'],
            'topics': ['technology', 'semiconductor'],
            'keywords': ['nvidia', 'government', 'AI', 'chips']
        }

        print(f"Query: {query}")
        print(f"User preferences: {user_prefs}")

        # Create enhanced planner directly
        print("\n=== Testing Enhanced Planner ===")
        from news_agent.integration.planner_aggregator import EnhancedPlannerAgent

        enhanced_planner = EnhancedPlannerAgent(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            enable_aggregation=True,
            max_concurrent_retrievers=3
        )

        # Test planner search
        planner_results = await enhanced_planner.run_async(query, user_preferences=user_prefs)
        print(f"Planner results keys: {list(planner_results.keys())}")

        if 'clustered_summaries' in planner_results:
            clustered_summaries = planner_results['clustered_summaries']
            print(f"Number of clustered summaries: {len(clustered_summaries)}")

            for i, summary in enumerate(clustered_summaries[:2]):
                print(f"\n  Cluster {i}:")
                print(f"    Title: {summary.get('title', 'No title')}")
                print(f"    Summary: {summary.get('summary', 'No summary')[:100]}...")
                print(f"    Key points: {len(summary.get('key_points', []))}")

                # Show key points
                key_points = summary.get('key_points', [])
                for j, kp in enumerate(key_points[:2]):
                    print(f"      KP {j+1}: {kp[:80]}...")

        elif 'summaries' in planner_results:
            summaries = planner_results['summaries']
            print(f"Number of summaries: {len(summaries)}")

            for i, summary in enumerate(summaries[:2]):
                print(f"\n  Summary {i}:")
                if isinstance(summary, str):
                    print(f"    Content: {summary[:100]}...")
                elif isinstance(summary, dict):
                    print(f"    Type: dict with keys {list(summary.keys())}")
                    if 'title' in summary:
                        print(f"    Title: {summary['title']}")
                    if 'summary' in summary:
                        print(f"    Summary: {summary['summary'][:100]}...")
                else:
                    print(f"    Type: {type(summary).__name__}")

        else:
            print("No summaries or clustered_summaries found!")

        # Check all available data in detail
        print("\nDetailed planner results analysis:")
        for key, value in planner_results.items():
            if isinstance(value, list):
                print(f"  {key}: {len(value)} items")
                if len(value) > 0 and key in ['breaking_news', 'financial_news', 'general_news', 'sec_filings']:
                    print(f"    Sample items from {key}:")
                    for i, item in enumerate(value[:2]):
                        if isinstance(item, dict):
                            title = item.get('title', item.get('headline', 'No title'))
                            url = item.get('url', item.get('href', 'No URL'))
                            print(f"      {i+1}. {title[:60]}... ({url[:50]}...)")
                        else:
                            print(f"      {i+1}. {str(item)[:100]}...")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())}")
                if key == 'aggregation':
                    agg = value
                    if 'clusters' in agg:
                        print(f"    aggregation has {len(agg['clusters'])} clusters")
                    if 'summaries' in agg:
                        print(f"    aggregation has {len(agg['summaries'])} summaries")
            else:
                print(f"  {key}: {type(value).__name__} = {value}")

        # Test key point extraction
        print("\n=== Testing Key Point Extraction ===")

        # Use the actual pipeline method
        key_points = pipeline._extract_key_points_from_aggregation(planner_results)
        print(f"Extracted key points: {len(key_points)}")

        for i, kp in enumerate(key_points):
            print(f"  KP {i+1}: {kp.get('query', 'No query')}")
            print(f"    Type: {kp.get('type', 'Unknown')}")
            print(f"    Original: {kp.get('original_title', kp.get('original_key_point', 'No original'))[:60]}...")

        # If no key points, try to extract manually
        if not key_points:
            print("\n=== Manual Key Point Extraction ===")

            # Try to find extractable content
            if 'clustered_summaries' in planner_results:
                for i, summary in enumerate(planner_results['clustered_summaries']):
                    title = summary.get('title', '')
                    if title:
                        manual_query = pipeline._create_focused_query(title)
                        print(f"  Manual query {i+1}: {manual_query}")

        # Cleanup
        enhanced_planner.cleanup()
        pipeline.cleanup()

    except Exception as e:
        print(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Pipeline Stage Debug")
    print("=" * 40)

    # Check environment
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        print("❌ Missing API keys")
        exit(1)

    print("✅ API keys found")
    asyncio.run(debug_pipeline_stages())