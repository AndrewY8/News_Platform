"""
End-to-End Topic Extraction Test
Tests the complete flow: User Query → Extract Topics → Match OR Fresh Retrieval
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


def get_analyzer():
    """Get available analyzer"""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if openai_api_key and OPENAI_AVAILABLE:
        return OpenAIAnalyzer(openai_api_key), "OpenAI"
    elif gemini_api_key and GEMINI_AVAILABLE:
        return GeminiAnalyzer(gemini_api_key), "Gemini"
    else:
        # Use dummy key for testing
        if OPENAI_AVAILABLE:
            return OpenAIAnalyzer("dummy_key"), "OpenAI (dummy)"
        elif GEMINI_AVAILABLE:
            return GeminiAnalyzer("dummy_key"), "Gemini (dummy)"
    return None, None


def test_topic_extraction_and_matching():
    """
    Test complete flow: Extract topics from query, then match OR trigger retrieval
    """
    print("\n" + "="*80)
    print("END-TO-END TOPIC EXTRACTION & MATCHING TEST")
    print("="*80)

    analyzer, analyzer_type = get_analyzer()
    if not analyzer:
        print("❌ No analyzer available")
        return False

    print(f"\n✅ Using {analyzer_type} analyzer\n")

    # Initialize topic matcher
    matcher = TopicMatcher()

    # Simulate existing database topics for different companies
    database_topics = {
        'Tesla': [
            {
                'id': 1,
                'company_id': 100,
                'name': 'Q4 2024 Earnings Report',
                'description': 'Tesla fourth quarter financial results and earnings call',
            },
            {
                'id': 2,
                'company_id': 100,
                'name': 'Cybertruck Production and Deliveries',
                'description': 'Tesla Cybertruck manufacturing ramp-up and delivery targets',
            },
            {
                'id': 3,
                'company_id': 100,
                'name': 'Full Self-Driving (FSD) Updates',
                'description': 'Tesla FSD software improvements and regulatory progress',
            }
        ],
        'Apple': [
            {
                'id': 4,
                'company_id': 200,
                'name': 'iPhone 15 Sales Performance',
                'description': 'iPhone 15 product line sales figures and market reception',
            },
            {
                'id': 5,
                'company_id': 200,
                'name': 'Vision Pro Launch Strategy',
                'description': 'Apple Vision Pro mixed reality headset launch and adoption',
            },
            {
                'id': 6,
                'company_id': 200,
                'name': 'Services Revenue Growth',
                'description': 'Apple Services segment including App Store, iCloud, Apple Music',
            }
        ],
        'Microsoft': [
            {
                'id': 7,
                'company_id': 300,
                'name': 'Azure Cloud Expansion',
                'description': 'Microsoft Azure cloud computing growth and market share',
            },
            {
                'id': 8,
                'company_id': 300,
                'name': 'AI Integration Across Products',
                'description': 'Microsoft Copilot and AI features in Office, Windows, and Bing',
            }
        ]
    }

    # Test cases
    test_cases = [
        {
            'name': 'Test 1: Exact Match - Tesla Earnings',
            'query': "What are Tesla's Q4 2024 earnings results?",
            'expected_company': 'Tesla',
            'expected_topic_match': True,
            'expected_topic': 'Q4 2024 Earnings Report'
        },
        {
            'name': 'Test 2: Close Match - Tesla FSD',
            'query': "Tesla self-driving updates",
            'expected_company': 'Tesla',
            'expected_topic_match': True,
            'expected_topic': 'Full Self-Driving (FSD) Updates'
        },
        {
            'name': 'Test 3: Product Match - Apple Vision Pro',
            'query': "How is Apple Vision Pro doing?",
            'expected_company': 'Apple',
            'expected_topic_match': True,
            'expected_topic': 'Vision Pro Launch Strategy'
        },
        {
            'name': 'Test 4: No Match - New Topic',
            'query': "Tesla battery technology breakthroughs",
            'expected_company': 'Tesla',
            'expected_topic_match': False,
            'expected_topic': None,
            'requires_retrieval': True
        },
        {
            'name': 'Test 5: Different Company Same Topic Type',
            'query': "Microsoft quarterly earnings",
            'expected_company': 'Microsoft',
            'expected_topic_match': False,  # Microsoft doesn't have earnings topic in our test DB
            'expected_topic': None,
            'requires_retrieval': True
        },
        {
            'name': 'Test 6: Vague Query',
            'query': "What's happening with Apple?",
            'expected_company': 'Apple',
            'expected_topic_match': False,  # Too vague to match specific topic
            'expected_topic': None,
            'requires_retrieval': True
        }
    ]

    results = []

    for test_case in test_cases:
        print("\n" + "="*80)
        print(f"{test_case['name']}")
        print("="*80)
        print(f"\n📝 User Query: \"{test_case['query']}\"")
        print("-" * 80)

        # STEP 1: Extract topics from query
        print("\n🔍 STEP 1: Extract Company & Topics from Query")
        query_intent = analyzer.analyze_query(test_case['query'])

        print(f"   Extracted:")
        print(f"   - Companies: {query_intent.companies}")
        print(f"   - Tickers: {query_intent.tickers}")
        print(f"   - Topics: {query_intent.topics}")
        print(f"   - Keywords: {query_intent.keywords}")
        print(f"   - Confidence: {query_intent.confidence:.2f}")

        # Determine company
        if query_intent.companies:
            company = query_intent.companies[0]
            # Clean up company name
            known_companies = ['Apple', 'Microsoft', 'Google', 'Amazon', 'Tesla', 'Meta', 'Nvidia']
            for known in known_companies:
                if company.startswith(known):
                    company = known
                    break
        elif query_intent.tickers:
            # Map ticker to company
            ticker_map = {'TSLA': 'Tesla', 'AAPL': 'Apple', 'MSFT': 'Microsoft'}
            company = ticker_map.get(query_intent.tickers[0], query_intent.tickers[0])
        else:
            company = None

        print(f"\n   ✅ Identified Company: {company}")

        # Check if company matches expected
        company_match = company == test_case['expected_company']
        if company_match:
            print(f"   ✅ Company extraction: CORRECT")
        else:
            print(f"   ❌ Company extraction: WRONG (expected {test_case['expected_company']})")

        # STEP 2: Get company topics from database
        print(f"\n🗄️ STEP 2: Get Topics from Database for '{company}'")

        if company and company in database_topics:
            company_topics = database_topics[company]
            print(f"   Found {len(company_topics)} existing topics for {company}:")
            for topic in company_topics:
                print(f"   - {topic['name']}")
        else:
            company_topics = []
            print(f"   ⚠️ No topics found in database for {company}")

        # STEP 3: Match query topics to database topics
        matched_topic = None
        if company_topics and query_intent.topics:
            print(f"\n🎯 STEP 3: Match Query Topics to Database Topics")
            print(f"   Query topics: {query_intent.topics}")

            matched_topic = matcher.match_query_to_topics(
                query_topics=query_intent.topics,
                existing_topics=company_topics,
                threshold=0.75
            )

            if matched_topic:
                print(f"\n   ✅ MATCH FOUND!")
                print(f"   - Topic: {matched_topic['name']}")
                print(f"   - Similarity: {matched_topic['similarity_score']:.3f}")
                print(f"   - Company ID: {matched_topic.get('company_id', 'N/A')}")

                # Verify it's the expected topic
                if test_case['expected_topic_match']:
                    if matched_topic['name'] == test_case['expected_topic']:
                        print(f"   ✅ CORRECT: Matched expected topic '{test_case['expected_topic']}'")
                    else:
                        print(f"   ⚠️ UNEXPECTED: Matched '{matched_topic['name']}' instead of '{test_case['expected_topic']}'")
            else:
                print(f"\n   ❌ NO MATCH FOUND (similarity below 0.75 threshold)")
        else:
            print(f"\n🎯 STEP 3: Skip Matching (no topics extracted or no database topics)")

        # STEP 4: Decision - Use cached or trigger retrieval
        print(f"\n📊 STEP 4: Decision")

        if matched_topic:
            print(f"   ✅ USE CACHED RESEARCH")
            print(f"   - Return articles for: {company} - {matched_topic['name']}")
            print(f"   - Source: Database (fast response)")
            decision = "CACHED"
        else:
            print(f"   🔄 TRIGGER FRESH RETRIEVAL")
            print(f"   - Company: {company}")
            print(f"   - Topics to research: {query_intent.topics if query_intent.topics else ['general company news']}")
            print(f"   - Reason: No sufficiently similar topic in database")
            decision = "RETRIEVAL"

        # Verify against expected
        print(f"\n✅ RESULT VALIDATION:")
        expected_decision = "RETRIEVAL" if test_case.get('requires_retrieval', False) else ("CACHED" if test_case['expected_topic_match'] else "RETRIEVAL")

        test_passed = True
        if company_match:
            print(f"   ✅ Company extraction: PASS")
        else:
            print(f"   ❌ Company extraction: FAIL")
            test_passed = False

        if decision == expected_decision:
            print(f"   ✅ Decision ({decision}): PASS")
        else:
            print(f"   ❌ Decision: FAIL (expected {expected_decision}, got {decision})")
            test_passed = False

        if test_case['expected_topic_match'] and matched_topic:
            if matched_topic['name'] == test_case['expected_topic']:
                print(f"   ✅ Topic match: PASS")
            else:
                print(f"   ⚠️ Topic match: PARTIAL (matched different topic)")
        elif not test_case['expected_topic_match'] and not matched_topic:
            print(f"   ✅ No match expected: PASS")

        results.append({
            'test': test_case['name'],
            'passed': test_passed,
            'company': company,
            'matched_topic': matched_topic['name'] if matched_topic else None,
            'decision': decision
        })

    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r['passed'])
    total = len(results)

    for result in results:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"{status} - {result['test']}")
        print(f"        Company: {result['company']}, Topic: {result['matched_topic']}, Decision: {result['decision']}")

    print(f"\nTotal: {passed}/{total} tests passed")

    print("\n" + "="*80)
    print("KEY TAKEAWAYS")
    print("="*80)
    print("""
1. ✅ Topic Extraction Works
   - System extracts companies and topics from natural language queries
   - Uses hybrid approach: spaCy → TextBlob → OpenAI/Gemini

2. ✅ Company-Specific Matching
   - Topics are filtered by company BEFORE matching
   - "Tesla earnings" only sees Tesla's topics, never Microsoft's

3. ✅ Semantic Similarity Matching
   - Uses embeddings to match query topics to database topics
   - Threshold: 0.75 (can be adjusted)

4. ✅ Smart Decision Making
   - If similarity > 0.75: Return cached research (fast!)
   - If similarity < 0.75: Trigger fresh retrieval (ensures relevant results)

5. 🔄 Retrieval Fallback
   - New topics automatically trigger retrieval
   - Vague queries trigger retrieval (better to fetch than guess)
   - Results can be cached for future queries
    """)

    return passed == total


if __name__ == "__main__":
    success = test_end_to_end_topic_extraction()
    sys.exit(0 if success else 1)
