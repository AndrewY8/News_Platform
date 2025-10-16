"""
Test script to see what creative queries are being generated
Run this to verify your analytical search intelligence is working
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from deep_news_agent.agents.search_agent import SearchAgent
from deep_news_agent.agents.interfaces import CompanyContext, Question

async def test_query_generation():
    """Test creative query generation"""

    print("\n" + "="*80)
    print("🧪 TESTING CREATIVE ANALYTICAL QUERY GENERATION")
    print("="*80 + "\n")

    # Initialize search agent
    openai_key = os.getenv('OPENAI_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')

    if not openai_key or not tavily_key:
        print("❌ Missing API keys in .env")
        return

    search_agent = SearchAgent(tavily_api_key=tavily_key, openai_api_key=openai_key)

    # Create a test company context
    context = CompanyContext(
        name="Microsoft",
        ticker="MSFT",
        industry="Technology",
        business_areas=["Cloud Computing (Azure)", "AI", "Microsoft 365", "Gaming"],
        current_status={"recent_focus": "AI and cloud expansion"}
    )

    # Create some test questions (simulating what orchestrator would generate)
    questions = [
        Question(text="What are recent AI infrastructure developments?", priority=1, iteration_number=1, topic_source="test"),
        Question(text="How is cloud competition evolving?", priority=2, iteration_number=1, topic_source="test"),
        Question(text="What regulatory changes affect the business?", priority=3, iteration_number=1, topic_source="test"),
    ]

    print("📋 Input Questions:")
    for q in questions:
        print(f"   - {q.text}")

    print("\n🤖 Generating creative analytical queries...\n")

    # Generate queries
    queries = await search_agent.generate_search_queries(questions, context)

    print("\n" + "="*80)
    print("🎯 GENERATED CREATIVE QUERIES:")
    print("="*80 + "\n")

    for i, query in enumerate(queries, 1):
        print(f"{i}. {query}\n")

    print("="*80)
    print(f"\n✅ Generated {len(queries)} analytical queries")
    print("\n💡 Analysis:")
    print(f"   - Average query length: {sum(len(q) for q in queries) / len(queries):.0f} chars")
    print(f"   - Queries with 'cause/effect': {sum(1 for q in queries if any(w in q.lower() for w in ['cause', 'effect', 'impact']))}")
    print(f"   - Cross-domain queries: {sum(1 for q in queries if any(w in q.lower() for w in ['banking', 'energy', 'real estate', 'labor']))}")
    print(f"   - Forward-looking queries: {sum(1 for q in queries if any(w in q.lower() for w in ['2025', 'outlook', 'forecast', 'future']))}")

    print("\n🎉 Test complete!\n")

if __name__ == "__main__":
    asyncio.run(test_query_generation())
