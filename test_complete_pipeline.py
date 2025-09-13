"""
Comprehensive Test Script for Enhanced News Discovery Pipeline

This script tests the complete end-to-end pipeline integration:
1. Enhanced News Discovery Pipeline (multi-stage)
2. Backend Service Integration
3. API Response Formatting
4. Performance and Quality Metrics

Run this to validate your complete implementation.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import components to test
from enhanced_news_pipeline import create_enhanced_news_pipeline
from backend.enhanced_pipeline_integration import get_enhanced_pipeline_news_service

def print_separator(title: str, char: str = "=", width: int = 70):
    """Print a formatted separator."""
    print(f"\n{char * width}")
    print(f" {title.center(width - 2)} ")
    print(f"{char * width}")

def print_stage_info(stage_name: str, duration: float, details: str = ""):
    """Print stage information."""
    print(f"  📊 {stage_name}: {duration:.2f}s")
    if details:
        print(f"     {details}")

def validate_environment() -> Dict[str, bool]:
    """Validate required environment variables."""
    print_separator("ENVIRONMENT VALIDATION")

    required_vars = {
        'GEMINI_API_KEY': 'Gemini AI (required for aggregation & summarization)',
        'TAVILY_API_KEY': 'Tavily Search (required for focused re-search)',
        'News_API_KEY': 'NewsAPI (fallback support)',
        'SEARCHAPI_API_KEY': 'SearchAPI (retrieval support)',
        'SERPER_API_KEY': 'Serper (retrieval support)'
    }

    validation_results = {}

    for var, description in required_vars.items():
        value = os.getenv(var)
        has_value = bool(value and value.strip())
        status = "✅" if has_value else "❌"
        print(f"  {status} {var}: {description}")
        validation_results[var] = has_value

    # Check critical requirements
    critical_missing = []
    if not validation_results['GEMINI_API_KEY']:
        critical_missing.append('GEMINI_API_KEY')
    if not validation_results['TAVILY_API_KEY']:
        critical_missing.append('TAVILY_API_KEY')

    if critical_missing:
        print(f"\n⚠️  CRITICAL: Missing required API keys: {', '.join(critical_missing)}")
        print("   The enhanced pipeline will not work without these keys.")
        return validation_results

    print(f"\n✅ Environment validation passed!")
    return validation_results

async def test_individual_pipeline(query: str, user_prefs: Dict = None) -> Dict[str, Any]:
    """Test the individual enhanced pipeline."""
    print_separator(f"TESTING INDIVIDUAL PIPELINE: '{query}'", "-")

    try:
        # Create pipeline
        pipeline = create_enhanced_news_pipeline(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            max_retrievers=3
        )

        # Test user preferences
        if not user_prefs:
            user_prefs = {
                'watchlist': ['TSLA', 'AAPL', 'MSFT'],
                'topics': ['technology', 'automotive'],
                'keywords': ['news', 'earnings', 'innovation']
            }

        print(f"🔍 Query: {query}")
        print(f"👤 User Preferences: {user_prefs}")

        # Run pipeline
        start_time = time.time()
        results = await pipeline.discover_news(query, user_prefs)
        total_time = time.time() - start_time

        # Validate results
        success = results['processing_stats']['success']
        print(f"\n📊 PIPELINE RESULTS:")
        print(f"  Success: {'✅' if success else '❌'}")
        print(f"  Total Duration: {total_time:.2f}s")

        if success:
            # Show stage breakdown
            stages = results.get('stages', {})
            for stage_name, stage_info in stages.items():
                stage_duration = stage_info.get('duration', 0)

                if 'retrieval' in stage_name:
                    details = f"Sources: {stage_info.get('total_sources', 0)}, Clusters: {stage_info.get('clusters_found', 0)}"
                elif 'extraction' in stage_name:
                    details = f"Key Points: {stage_info.get('key_points_found', 0)}"
                elif 'focused_search' in stage_name:
                    details = f"Queries: {stage_info.get('search_queries', 0)}, Articles: {stage_info.get('articles_found', 0)}"
                elif 'curation' in stage_name:
                    details = f"Final Articles: {stage_info.get('final_articles', 0)}"
                else:
                    details = ""

                print_stage_info(stage_name.replace('_', ' ').title(), stage_duration, details)

            # Show final results
            final_articles = results.get('final_articles', [])
            key_points = results.get('key_points', [])

            print(f"\n🎯 FINAL RESULTS:")
            print(f"  Key Points Extracted: {len(key_points)}")
            print(f"  Final Curated Articles: {len(final_articles)}")

            if key_points:
                print(f"\n📝 Key Points:")
                for i, kp in enumerate(key_points[:3], 1):
                    print(f"  {i}. {kp.get('query', 'N/A')}")

            if final_articles:
                print(f"\n📰 Sample Articles:")
                for i, article in enumerate(final_articles[:3], 1):
                    title = article.get('title', 'No title')[:60]
                    source = article.get('source', 'Unknown')
                    score = article.get('relevance_score', 0)
                    print(f"  {i}. {title}... ({source}, Score: {score:.2f})")

        else:
            error = results['processing_stats'].get('error', 'Unknown error')
            print(f"❌ Pipeline failed: {error}")

        # Cleanup
        pipeline.cleanup()

        return results

    except Exception as e:
        print(f"❌ Individual pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return {'processing_stats': {'success': False, 'error': str(e)}}

async def test_integrated_service(query: str, user_tickers: List[str] = None) -> Dict[str, Any]:
    """Test the integrated backend service."""
    print_separator(f"TESTING INTEGRATED SERVICE: '{query}'", "-")

    try:
        # Get the integrated service
        service = get_enhanced_pipeline_news_service()

        # Get service stats
        stats = service.get_service_stats()
        print(f"🔧 Service Stats: {stats}")

        # Test user tickers
        if not user_tickers:
            user_tickers = ['TSLA', 'AAPL', 'MSFT', 'GOOGL']

        print(f"🔍 Query: {query}")
        print(f"📈 User Tickers: {user_tickers}")

        # Test enhanced response
        start_time = time.time()
        response = await service.generate_enhanced_chat_response(
            message=query,
            user_tickers=user_tickers,
            use_enhanced_pipeline=True,
            conversation_history=[]
        )
        total_time = time.time() - start_time

        # Validate response
        print(f"\n📊 SERVICE RESPONSE:")
        print(f"  Success: {'✅' if response.get('success') else '❌'}")
        print(f"  Total Duration: {total_time:.2f}s")
        print(f"  Search Method: {response.get('search_method', 'unknown')}")
        print(f"  Enhanced Pipeline Used: {'✅' if response.get('enhanced_pipeline_used') else '❌'}")

        # Show response details
        ai_response = response.get('response', '')
        suggested_articles = response.get('suggested_articles', [])

        print(f"\n💬 AI Response: {ai_response[:200]}...")
        print(f"📰 Suggested Articles: {len(suggested_articles)}")

        # Show pipeline metadata if available
        pipeline_metadata = response.get('pipeline_metadata')
        if pipeline_metadata:
            print(f"\n🚀 Pipeline Metadata:")
            print(f"  Processing Time: {pipeline_metadata.get('total_duration', 0):.2f}s")
            print(f"  Stages Completed: {pipeline_metadata.get('stages_completed', 0)}")
            print(f"  Key Points: {pipeline_metadata.get('key_points_extracted', 0)}")
            print(f"  Final Articles: {pipeline_metadata.get('final_article_count', 0)}")

        # Show sources
        sources_used = response.get('sources_used', [])
        if sources_used:
            print(f"  Sources Used: {', '.join(sources_used)}")

        # Show sample articles
        if suggested_articles:
            print(f"\n📄 Sample Suggested Articles:")
            for i, article in enumerate(suggested_articles[:3], 1):
                title = article.get('title', 'No title')[:60]
                source = article.get('source', 'Unknown')
                score = article.get('relevance_score', 0)
                tags = ', '.join(article.get('tags', [])[:3])
                print(f"  {i}. {title}... ({source}, Score: {score:.2f})")
                if tags:
                    print(f"     Tags: {tags}")

        # Cleanup
        service.cleanup()

        return response

    except Exception as e:
        print(f"❌ Integrated service test failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def compare_results(individual_results: Dict, service_results: Dict):
    """Compare results from individual pipeline vs integrated service."""
    print_separator("RESULTS COMPARISON")

    individual_success = individual_results.get('processing_stats', {}).get('success', False)
    service_success = service_results.get('success', False)

    print(f"Individual Pipeline Success: {'✅' if individual_success else '❌'}")
    print(f"Integrated Service Success: {'✅' if service_success else '❌'}")

    if individual_success and service_success:
        # Compare article counts
        individual_articles = len(individual_results.get('final_articles', []))
        service_articles = len(service_results.get('suggested_articles', []))

        print(f"\nArticle Count Comparison:")
        print(f"  Individual Pipeline: {individual_articles} articles")
        print(f"  Integrated Service: {service_articles} articles")

        # Compare processing times
        individual_time = individual_results.get('processing_stats', {}).get('total_duration', 0)
        service_time = service_results.get('processing_time', 0)

        print(f"\nProcessing Time Comparison:")
        print(f"  Individual Pipeline: {individual_time:.2f}s")
        print(f"  Integrated Service: {service_time:.2f}s")

        # Check consistency
        if abs(individual_articles - service_articles) <= 2 and abs(individual_time - service_time) <= 5:
            print(f"\n✅ Results are consistent between pipeline and service!")
        else:
            print(f"\n⚠️  Results differ significantly - may indicate integration issues")

    else:
        print(f"\n❌ Cannot compare - one or both tests failed")

async def run_comprehensive_tests():
    """Run comprehensive tests for the entire system."""
    print_separator("COMPREHENSIVE PIPELINE TESTING")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Step 1: Environment validation
    env_validation = validate_environment()
    critical_missing = not (env_validation.get('GEMINI_API_KEY') and env_validation.get('TAVILY_API_KEY'))

    if critical_missing:
        print(f"\n❌ Cannot proceed with tests - missing critical API keys")
        print(f"Please add GEMINI_API_KEY and TAVILY_API_KEY to your .env file")
        return

    # Test queries
    test_queries = [
        {
            'query': 'Tesla autonomous driving latest developments',
            'user_prefs': {
                'watchlist': ['TSLA'],
                'topics': ['automotive', 'technology'],
                'keywords': ['autonomous', 'self-driving', 'AI']
            },
            'user_tickers': ['TSLA', 'NVDA']
        },
        {
            'query': 'Apple iPhone sales and revenue report',
            'user_prefs': {
                'watchlist': ['AAPL'],
                'topics': ['technology', 'consumer_electronics'],
                'keywords': ['iPhone', 'sales', 'revenue', 'earnings']
            },
            'user_tickers': ['AAPL']
        },
        {
            'query': 'Microsoft Azure cloud growth',
            'user_prefs': {
                'watchlist': ['MSFT'],
                'topics': ['technology', 'cloud_computing'],
                'keywords': ['Azure', 'cloud', 'growth', 'AI']
            },
            'user_tickers': ['MSFT', 'AMZN', 'GOOGL']
        }
    ]

    all_results = []

    for i, test_case in enumerate(test_queries, 1):
        print_separator(f"TEST CASE {i}: {test_case['query'][:40]}...")

        try:
            # Test individual pipeline
            individual_results = await test_individual_pipeline(
                test_case['query'],
                test_case['user_prefs']
            )

            await asyncio.sleep(2)  # Brief pause between tests

            # Test integrated service
            service_results = await test_integrated_service(
                test_case['query'],
                test_case['user_tickers']
            )

            # Compare results
            compare_results(individual_results, service_results)

            # Store results for summary
            all_results.append({
                'query': test_case['query'],
                'individual_success': individual_results.get('processing_stats', {}).get('success', False),
                'service_success': service_results.get('success', False),
                'individual_articles': len(individual_results.get('final_articles', [])),
                'service_articles': len(service_results.get('suggested_articles', [])),
                'individual_time': individual_results.get('processing_stats', {}).get('total_duration', 0),
                'service_time': service_results.get('processing_time', 0)
            })

        except Exception as e:
            print(f"❌ Test case {i} failed: {e}")
            all_results.append({
                'query': test_case['query'],
                'individual_success': False,
                'service_success': False,
                'error': str(e)
            })

    # Final summary
    print_separator("COMPREHENSIVE TEST SUMMARY")

    successful_tests = sum(1 for r in all_results if r.get('individual_success') and r.get('service_success'))
    total_tests = len(all_results)

    print(f"Overall Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")

    if successful_tests > 0:
        avg_individual_time = sum(r.get('individual_time', 0) for r in all_results if r.get('individual_success')) / successful_tests
        avg_service_time = sum(r.get('service_time', 0) for r in all_results if r.get('service_success')) / successful_tests
        avg_articles = sum(r.get('service_articles', 0) for r in all_results if r.get('service_success')) / successful_tests

        print(f"\nPerformance Metrics:")
        print(f"  Average Pipeline Time: {avg_individual_time:.2f}s")
        print(f"  Average Service Time: {avg_service_time:.2f}s")
        print(f"  Average Articles Returned: {avg_articles:.1f}")

    print(f"\n📋 Test Results Detail:")
    for i, result in enumerate(all_results, 1):
        status = "✅" if result.get('individual_success') and result.get('service_success') else "❌"
        query = result['query'][:50] + "..." if len(result['query']) > 50 else result['query']
        articles = result.get('service_articles', 0)
        time_taken = result.get('service_time', 0)
        print(f"  {status} Test {i}: {query} ({articles} articles, {time_taken:.1f}s)")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"comprehensive_test_results_{timestamp}.json"

    try:
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'environment_validation': env_validation,
                'test_results': all_results,
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'success_rate': successful_tests/total_tests*100 if total_tests > 0 else 0
                }
            }, f, indent=2, default=str)

        print(f"\n💾 Detailed results saved to: {results_file}")

    except Exception as e:
        print(f"⚠️  Could not save results file: {e}")

    if successful_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! Your enhanced pipeline is working perfectly!")
        print(f"🚀 Ready for production integration!")
    elif successful_tests > 0:
        print(f"\n✅ {successful_tests} out of {total_tests} tests passed.")
        print(f"🔧 Check failed tests and API key configuration.")
    else:
        print(f"\n❌ All tests failed. Check your configuration and API keys.")

async def main():
    """Main test function."""
    try:
        await run_comprehensive_tests()
    except KeyboardInterrupt:
        print(f"\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Enhanced News Discovery Pipeline - Comprehensive Test Suite")
    asyncio.run(main())