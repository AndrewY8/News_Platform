#!/usr/bin/env python3
"""
Quick test to verify the improved article formatting and titles.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, '/home/patrick/Documents/News_Platform')

load_dotenv()

async def test_article_formatting():
    """Test article formatting with the enhanced pipeline."""
    print("🧪 Testing Article Formatting")
    print("=" * 40)

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

        # Run pipeline
        results = await pipeline.discover_news(query, user_prefs)

        if results['processing_stats']['success']:
            final_articles = results.get('final_articles', [])
            print(f"\n✅ Success! Found {len(final_articles)} articles")

            print("\n📰 Article Details:")
            for i, article in enumerate(final_articles[:5]):
                print(f"\n  Article {i+1}:")
                print(f"    📰 Title: {article.get('title', 'No title')}")
                print(f"    🏢 Source: {article.get('source', 'Unknown')}")
                print(f"    🔗 URL: {article.get('url', 'No URL')[:60]}...")
                print(f"    📊 Score: {article.get('relevance_score', 0):.2f}")
                print(f"    📝 Preview: {article.get('preview', article.get('content', ''))[:100]}...")
                print(f"    🏷️  Tags: {article.get('tags', [])}")
                print(f"    📅 Time: {article.get('timestamp', 'No timestamp')}")
        else:
            error = results['processing_stats'].get('error', 'Unknown error')
            print(f"❌ Failed: {error}")

        # Cleanup
        pipeline.cleanup()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_article_formatting())