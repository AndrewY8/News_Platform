#!/usr/bin/env python3
"""
Simple test to verify Tavily search with the enhanced pipeline.
Focus on the core issue: why articles are being filtered out.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project path
sys.path.insert(0, '/home/patrick/Documents/News_Platform')

load_dotenv()

async def test_nvidia_query():
    """Test the specific Nvidia query that's failing."""
    print("Testing Nvidia query with enhanced pipeline...")

    try:
        from enhanced_news_pipeline import create_enhanced_news_pipeline

        # Initialize pipeline
        pipeline = create_enhanced_news_pipeline(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            max_retrievers=3
        )

        # Test the specific query
        query = "Nvidia recent news with US government"
        user_prefs = {
            'watchlist': ['NVDA'],
            'topics': ['technology', 'semiconductor'],
            'keywords': ['nvidia', 'government', 'AI', 'chips']
        }

        print(f"Query: {query}")
        print(f"User preferences: {user_prefs}")

        # Run the pipeline
        results = await pipeline.discover_news(query, user_prefs)

        # Check results
        success = results['processing_stats']['success']
        print(f"\nPipeline Success: {success}")

        if success:
            final_articles = results.get('final_articles', [])
            print(f"Final articles found: {len(final_articles)}")

            # Show article details
            for i, article in enumerate(final_articles[:3]):
                print(f"\n  Article {i+1}:")
                print(f"    Title: {article.get('title', 'No title')}")
                print(f"    Source: {article.get('source', 'Unknown')}")
                print(f"    URL: {article.get('url', 'No URL')[:80]}...")
                print(f"    Score: {article.get('relevance_score', 0):.2f}")
                print(f"    Preview: {article.get('content', '')[:100]}...")

            # Show processing stats
            processing_time = results['processing_stats'].get('total_duration', 0)
            print(f"\nProcessing time: {processing_time:.2f} seconds")

            # Show stage details
            stages = results.get('stages', {})
            for stage_name, stage_info in stages.items():
                print(f"  {stage_name}: {stage_info.get('duration', 0):.2f}s")
        else:
            error = results['processing_stats'].get('error', 'Unknown error')
            print(f"Pipeline failed: {error}")

        # Cleanup
        pipeline.cleanup()
        return results

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🧪 Simple Tavily Test for Enhanced Pipeline")
    print("=" * 50)

    # Check environment
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ TAVILY_API_KEY not found")
        exit(1)

    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found")
        exit(1)

    print("✅ API keys found")

    # Run test
    results = asyncio.run(test_nvidia_query())

    if results and results['processing_stats']['success']:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed or returned no results")