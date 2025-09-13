"""
Debug script to investigate why Tavily search returns 0 articles.
This will help identify if the issue is with:
1. Tavily API calls
2. Quality filtering being too strict
3. Domain restrictions
4. Article validation logic
"""

import asyncio
import os
import json
import time
from dotenv import load_dotenv
import sys

# Add the project directory to Python path
sys.path.insert(0, '/home/patrick/Documents/News_Platform')

from enhanced_news_pipeline import create_enhanced_news_pipeline
from news_agent.retrievers.tavily.tavily_search import TavilyRetriever

load_dotenv()

async def debug_tavily_direct_search():
    """Test Tavily search directly without pipeline."""
    print("=== DIRECT TAVILY SEARCH DEBUG ===")

    # Test direct Tavily search
    test_queries = [
        "Nvidia recent news with US government",
        "Nvidia AI chips government contracts",
        "Nvidia financial news government",
        "NVDA news government contracts"
    ]

    premium_domains = [
        "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
        "cnbc.com", "marketwatch.com", "apnews.com"
    ]

    for query in test_queries:
        print(f"\n--- Testing query: '{query}' ---")

        try:
            # Test 1: Basic Tavily search without domain restrictions
            print("1. Basic Tavily search (no domain restrictions):")
            tavily_basic = TavilyRetriever(
                query=query,
                topic="news"
            )

            basic_results = tavily_basic.search(max_results=5)
            print(f"   Basic search results: {len(basic_results)}")

            if basic_results:
                for i, article in enumerate(basic_results[:3]):
                    url = article.get('href', 'No URL')
                    title = article.get('title', 'No title')
                    print(f"   {i+1}. {title[:60]}... ({url})")

            # Test 2: Tavily search with domain restrictions
            print("\n2. Domain-restricted Tavily search:")
            tavily_restricted = TavilyRetriever(
                query=f"news article {query} financial reporting",
                topic="news",
                query_domains=premium_domains
            )

            restricted_results = tavily_restricted.search(max_results=8)
            print(f"   Domain-restricted results: {len(restricted_results)}")

            if restricted_results:
                for i, article in enumerate(restricted_results[:3]):
                    url = article.get('href', 'No URL')
                    title = article.get('title', 'No title')
                    body = article.get('body', '')[:100]
                    print(f"   {i+1}. {title[:60]}... ({url})")
                    print(f"      Body: {body}...")
            else:
                print("   No articles found with domain restrictions")

        except Exception as e:
            print(f"   ERROR: {e}")

async def debug_pipeline_stages():
    """Debug each pipeline stage to identify where articles are lost."""
    print("\n=== PIPELINE STAGE DEBUG ===")

    query = "Nvidia recent news with US government"
    user_prefs = {
        'watchlist': ['NVDA'],
        'topics': ['technology', 'semiconductor'],
        'keywords': ['nvidia', 'government', 'AI', 'chips']
    }

    try:
        # Create pipeline with debug logging
        pipeline = create_enhanced_news_pipeline(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            max_retrievers=3
        )

        print(f"Query: {query}")
        print(f"User preferences: {user_prefs}")

        # Test Stage 1: Enhanced planner retrieval
        print("\n--- STAGE 1: Enhanced Planner Retrieval ---")
        retrieval_results = await pipeline._enhanced_retrieval(query, user_prefs)

        print(f"Retrieval results keys: {list(retrieval_results.keys())}")
        if 'clustered_summaries' in retrieval_results:
            summaries = retrieval_results['clustered_summaries']
            print(f"Number of clustered summaries: {len(summaries)}")

            for i, summary in enumerate(summaries[:3]):
                print(f"  Cluster {i}: {summary.get('summary', '')[:100]}...")

        # Test Stage 2: Key point extraction
        print("\n--- STAGE 2: Key Point Extraction ---")
        key_points = await pipeline._extract_key_points(retrieval_results, user_prefs)
        print(f"Number of key points extracted: {len(key_points)}")

        for i, kp in enumerate(key_points[:5]):
            print(f"  {i+1}. Query: {kp.get('query', 'No query')}")
            print(f"      Original: {kp.get('original_key_point', '')[:80]}...")

        # Test Stage 3: Tavily search with detailed logging
        print("\n--- STAGE 3: Tavily Search (Detailed) ---")

        if key_points:
            # Test one key point in detail
            test_kp = key_points[0]
            print(f"Testing key point: {test_kp['query']}")

            # Simulate the single Tavily search with more logging
            premium_domains = [
                "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
                "cnbc.com", "marketwatch.com", "apnews.com"
            ]

            enhanced_query = f"news article {test_kp['query']} financial reporting"
            print(f"Enhanced query: {enhanced_query}")

            tavily_retriever = TavilyRetriever(
                query=enhanced_query,
                topic="news",
                query_domains=premium_domains
            )

            search_results = tavily_retriever.search(max_results=8)
            print(f"Raw Tavily results: {len(search_results)}")

            if search_results:
                print("Raw results analysis:")
                for i, article in enumerate(search_results):
                    url = article.get('href', 'No URL')
                    title = article.get('title', 'No title')
                    body_length = len(article.get('body', ''))

                    print(f"  {i+1}. Title: {title[:60]}...")
                    print(f"      URL: {url}")
                    print(f"      Body length: {body_length}")

                    # Check domain validation
                    domain = pipeline._extract_domain(url)
                    domain_allowed = any(allowed_domain in domain for allowed_domain in premium_domains)
                    print(f"      Domain: {domain} (Allowed: {domain_allowed})")

                    # Check quality validation step by step
                    if body_length >= 100 and domain_allowed:
                        # Test title extraction
                        extracted_title = pipeline._extract_proper_article_title(article.get('body', ''), url)
                        print(f"      Extracted title: {extracted_title}")

                        # Test content quality
                        if extracted_title:
                            is_quality = pipeline._is_quality_news_content(article.get('body', ''), extracted_title)
                            print(f"      Quality check: {is_quality}")

                            # Test news article check
                            is_news = pipeline._is_news_article(article.get('body', ''), url)
                            print(f"      News check: {is_news}")

                    print()

            # Now test the full validation pipeline
            print("Full validation pipeline:")
            validated_articles = []
            for article in search_results:
                article_data = pipeline._extract_and_validate_article(article, test_kp['query'], test_kp, premium_domains)
                if article_data:
                    validated_articles.append(article_data)

            print(f"Articles that passed full validation: {len(validated_articles)}")

        pipeline.cleanup()

    except Exception as e:
        print(f"Pipeline debug failed: {e}")
        import traceback
        traceback.print_exc()

async def debug_quality_filters():
    """Test the quality filtering functions with sample content."""
    print("\n=== QUALITY FILTER DEBUG ===")

    # Create pipeline to access filtering methods
    pipeline = create_enhanced_news_pipeline(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        max_retrievers=1
    )

    # Test with different types of content
    test_contents = [
        {
            'title': 'Nvidia Reports Strong Q3 Earnings Driven by AI Chip Demand',
            'content': 'Nvidia Corporation reported strong third-quarter earnings today, driven by increased demand for artificial intelligence chips from government and enterprise customers. The company announced revenue of $18.1 billion...',
            'url': 'https://reuters.com/technology/nvidia-reports-q3-earnings-2024',
            'should_pass': True
        },
        {
            'title': 'Subscribe to Our Newsletter - Get Latest News',
            'content': 'Subscribe to our newsletter to get the latest financial news delivered to your inbox daily. Sign up now for free updates...',
            'url': 'https://bloomberg.com/subscribe',
            'should_pass': False
        },
        {
            'title': 'Contact Us - Bloomberg News',
            'content': 'Contact Bloomberg News for press inquiries, editorial feedback, or to report news tips. Our newsroom is available 24/7...',
            'url': 'https://bloomberg.com/contact',
            'should_pass': False
        }
    ]

    print("Testing quality filters:")
    for i, test in enumerate(test_contents):
        print(f"\n--- Test {i+1} (Should pass: {test['should_pass']}) ---")
        print(f"URL: {test['url']}")
        print(f"Title: {test['title']}")

        # Test individual filter components
        domain = pipeline._extract_domain(test['url'])
        print(f"Domain: {domain}")

        premium_domains = ["reuters.com", "bloomberg.com", "wsj.com"]
        domain_allowed = any(allowed_domain in domain for allowed_domain in premium_domains)
        print(f"Domain allowed: {domain_allowed}")

        extracted_title = pipeline._extract_proper_article_title(test['content'], test['url'])
        print(f"Extracted title: {extracted_title}")

        if extracted_title:
            is_valid_title = pipeline._is_valid_title(extracted_title)
            print(f"Valid title: {is_valid_title}")

            is_quality = pipeline._is_quality_news_content(test['content'], extracted_title)
            print(f"Quality content: {is_quality}")

            is_news = pipeline._is_news_article(test['content'], test['url'])
            print(f"Is news article: {is_news}")

            # Final validation
            article_data = pipeline._extract_and_validate_article(
                {'href': test['url'], 'body': test['content'], 'title': test['title']},
                'nvidia news',
                {'cluster_id': 1, 'priority': 2},
                premium_domains
            )

            passed_validation = article_data is not None
            print(f"FINAL RESULT: {'PASSED' if passed_validation else 'FAILED'}")

            if test['should_pass'] != passed_validation:
                print(f"⚠️ UNEXPECTED RESULT! Expected {test['should_pass']}, got {passed_validation}")

    pipeline.cleanup()

async def main():
    """Run all debug tests."""
    print("🐛 Tavily Search Debug Suite")
    print("=" * 50)

    # Check environment
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ TAVILY_API_KEY not found in environment")
        return

    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found in environment")
        return

    print("✅ API keys found")

    # Run debug tests
    await debug_tavily_direct_search()
    await debug_pipeline_stages()
    await debug_quality_filters()

    print("\n🔍 Debug complete! Check the output above for issues.")

if __name__ == "__main__":
    asyncio.run(main())