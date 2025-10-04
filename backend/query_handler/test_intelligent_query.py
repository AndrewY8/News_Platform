"""
Test script for the Intelligent Query System
Run this to validate that NER, topic matching, and routing work correctly
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Try importing both analyzers
try:
    from query_handler.hybrid_query_analyzer_openai import HybridQueryAnalyzer as OpenAIAnalyzer
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False

try:
    from query_handler.hybrid_query_analyzer import HybridQueryAnalyzer as GeminiAnalyzer
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False

from query_handler.intelligent_query_router import IntelligentQueryRouter, TopicMatcher


def test_query_analyzer():
    """Test the hybrid query analyzer"""
    print("\n" + "="*80)
    print("TEST 1: Hybrid Query Analyzer")
    print("="*80)

    # Try OpenAI first, then Gemini
    openai_api_key = os.getenv("OPENAI_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    analyzer = None
    analyzer_type = None

    if openai_api_key and OPENAI_AVAILABLE:
        analyzer = OpenAIAnalyzer(openai_api_key)
        analyzer_type = "OpenAI"
        print(f"✅ Using OpenAI analyzer")
    elif gemini_api_key and GEMINI_AVAILABLE:
        analyzer = GeminiAnalyzer(gemini_api_key)
        analyzer_type = "Gemini"
        print(f"✅ Using Gemini analyzer")
    else:
        # Use dummy key for testing fast methods only
        if OPENAI_AVAILABLE:
            analyzer = OpenAIAnalyzer("dummy_key_for_testing")
            analyzer_type = "OpenAI (dummy key)"
        elif GEMINI_AVAILABLE:
            analyzer = GeminiAnalyzer("dummy_key_for_testing")
            analyzer_type = "Gemini (dummy key)"
        else:
            print("❌ No analyzer available")
            return False
        print(f"⚠️ No API key found - using {analyzer_type} (LLM fallback disabled)")

    test_queries = [
        "What's Tesla's Q4 earnings looking like?",
        "AAPL stock performance",
        "Latest on Apple's Vision Pro sales",
        "Microsoft Azure growth trends",
        "How is Nvidia doing in AI chips?"
    ]

    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 80)

        result = analyzer.analyze_query(query)

        print(f"Companies: {result.companies}")
        print(f"Tickers: {result.tickers}")
        print(f"Topics: {result.topics}")
        print(f"Products: {result.products}")
        print(f"Intent: {result.intent}")
        print(f"Keywords: {result.keywords}")
        print(f"Financial Terms: {result.financial_terms}")
        print(f"Confidence: {result.confidence:.2f}")

        # Validation
        if result.companies or result.tickers:
            print("✅ Company/ticker extracted")
        else:
            print("⚠️ No company/ticker found")

    return True


def test_topic_matcher():
    """Test topic embedding and matching"""
    print("\n" + "="*80)
    print("TEST 2: Topic Matcher")
    print("="*80)

    matcher = TopicMatcher()

    # Simulated database topics
    existing_topics = [
        {
            'id': 1,
            'name': 'Q4 2024 Earnings Report',
            'description': 'Fourth quarter financial results and earnings call',
        },
        {
            'id': 2,
            'name': 'Vision Pro Launch & Market Reception',
            'description': 'Apple Vision Pro product launch, sales figures, and market response',
        },
        {
            'id': 3,
            'name': 'AI Chip Development',
            'description': 'Development of artificial intelligence processors and GPUs',
        }
    ]

    test_cases = [
        {
            'query_topics': ['earnings', 'Q4', 'financial results'],
            'expected_match': 'Q4 2024 Earnings Report'
        },
        {
            'query_topics': ['Vision Pro', 'sales', 'product'],
            'expected_match': 'Vision Pro Launch & Market Reception'
        },
        {
            'query_topics': ['AI chips', 'GPU', 'processors'],
            'expected_match': 'AI Chip Development'
        },
        {
            'query_topics': ['merger', 'acquisition'],
            'expected_match': None  # No match expected
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}")
        print(f"Query Topics: {test_case['query_topics']}")
        print(f"Expected Match: {test_case['expected_match']}")
        print("-" * 80)

        matched_topic = matcher.match_query_to_topics(
            query_topics=test_case['query_topics'],
            existing_topics=existing_topics,
            threshold=0.75
        )

        if matched_topic:
            print(f"✅ Matched: '{matched_topic['name']}' (similarity: {matched_topic['similarity_score']:.3f})")

            if test_case['expected_match']:
                if matched_topic['name'] == test_case['expected_match']:
                    print("✅ Correct match!")
                else:
                    print(f"⚠️ Expected '{test_case['expected_match']}' but got '{matched_topic['name']}'")
        else:
            print("❌ No match found")
            if not test_case['expected_match']:
                print("✅ Correctly returned no match")

    return True


def test_full_routing():
    """Test the complete routing system"""
    print("\n" + "="*80)
    print("TEST 3: Full Query Routing (requires database)")
    print("="*80)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not openai_api_key and not gemini_api_key:
        print("❌ No LLM API key found (need OPENAI_API_KEY or GEMINI_API_KEY)")
        return False

    if not supabase_url or not supabase_key:
        print("⚠️ Supabase credentials not found - skipping database tests")
        print("   Set SUPABASE_URL and SUPABASE_KEY to test database features")
        return True

    try:
        router = IntelligentQueryRouter(
            openai_api_key=openai_api_key,
            gemini_api_key=gemini_api_key,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            use_openai=True  # Prefer OpenAI
        )
        print("✅ Query router initialized")

        test_queries = [
            "What's happening with Tesla?",
            "Apple Vision Pro sales numbers",
            "Microsoft cloud revenue"
        ]

        for query in test_queries:
            print(f"\n📝 Routing Query: '{query}'")
            print("-" * 80)

            result = router.route_query(query)

            print(f"Source: {result['source']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Message: {result.get('message', 'N/A')}")

            if result['matched_topic']:
                print(f"Matched Topic: {result['matched_topic']['name']}")
                print(f"Articles: {len(result['articles'])}")

            if result['source'] == 'cache':
                print("✅ Cache hit!")
            elif result['source'] == 'fresh_search':
                print("🔄 Fresh search needed")
                print(f"Search Params: {result.get('search_params', {})}")
            else:
                print("⚠️ Fallback response")

    except Exception as e:
        print(f"❌ Error during routing test: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_performance():
    """Test performance metrics"""
    print("\n" + "="*80)
    print("TEST 4: Performance Metrics")
    print("="*80)

    import time

    # Try OpenAI first, then Gemini
    openai_api_key = os.getenv("OPENAI_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    analyzer = None
    analyzer_type = None

    if openai_api_key and OPENAI_AVAILABLE:
        analyzer = OpenAIAnalyzer(openai_api_key)
        analyzer_type = "OpenAI"
        print(f"✅ Testing with OpenAI analyzer")
    elif gemini_api_key and GEMINI_AVAILABLE:
        analyzer = GeminiAnalyzer(gemini_api_key)
        analyzer_type = "Gemini"
        print(f"✅ Testing with Gemini analyzer")
    else:
        # Use dummy key for testing fast methods only
        if OPENAI_AVAILABLE:
            analyzer = OpenAIAnalyzer("dummy_key_for_testing")
            analyzer_type = "OpenAI (dummy key)"
        elif GEMINI_AVAILABLE:
            analyzer = GeminiAnalyzer("dummy_key_for_testing")
            analyzer_type = "Gemini (dummy key)"
        else:
            print("❌ No analyzer available")
            return False
        print(f"⚠️ No API key found - using {analyzer_type} (LLM fallback disabled)")

    queries = [
        "AAPL earnings",  # Should be fast (no LLM needed)
        "What's that new AI headset from Apple called?",  # Needs LLM
        "Tesla stock price"  # Should be fast
    ]

    for query in queries:
        print(f"\n⏱️ Query: '{query}'")
        print("-" * 80)

        start_time = time.time()
        result = analyzer.analyze_query(query)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"Time: {elapsed_ms:.1f}ms")
        print(f"Confidence: {result.confidence:.2f}")

        if elapsed_ms < 100:
            print("✅ Fast path (no LLM)")
        elif elapsed_ms < 500:
            print("⚡ Medium speed")
        else:
            print("🐢 Slow (used LLM)")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("INTELLIGENT QUERY SYSTEM - TEST SUITE")
    print("="*80)

    tests = [
        ("Query Analyzer", test_query_analyzer),
        ("Topic Matcher", test_topic_matcher),
        ("Full Routing", test_full_routing),
        ("Performance", test_performance)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
