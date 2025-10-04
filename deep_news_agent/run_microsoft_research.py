"""
Run Deep Research on Microsoft using Earnings Call Transcript

This script runs the deep research pipeline for Microsoft (MSFT) using
the earnings call transcript from prompts.py as additional context.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from deep_news_agent.agents.orchestrator_agent import OrchestratorAgent
from deep_news_agent.agents.interfaces import CompanyContext, PipelineConfig
from deep_news_agent.db.research_db_manager import ResearchDBManager
from deep_news_agent.prompts.prompts import MICROSOFT_EARNINGS

# Load environment from root directory
load_dotenv(Path(__file__).parent.parent / '.env')


async def run_microsoft_research(max_iterations=3):
    """
    Run deep research for Microsoft using earnings transcript context

    Args:
        max_iterations: Number of research iterations (default: 3)
    """

    print("="*80)
    print("🔬 MICROSOFT DEEP RESEARCH PIPELINE")
    print("="*80)
    print(f"\n📊 Using earnings call transcript as context")
    print(f"🔄 Running {max_iterations} research iterations\n")

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return

    # Initialize database manager
    print("🔌 Connecting to Supabase database...")
    db_manager = ResearchDBManager(supabase_url, supabase_key)

    # Create Microsoft company context
    # Extract key insights from earnings transcript for context
    microsoft_context = CompanyContext(
        name="MSFT",  # Ticker symbol for database storage
        ticker="MSFT",
        industry="Technology - Cloud Computing & AI",
        business_areas=[
            "Cloud Computing (Azure)",
            "AI Infrastructure & Models",
            "Microsoft 365 & Productivity",
            "Copilot AI Assistant",
            "Database & Analytics (Fabric)",
            "Security & Identity (Entra, Defender)",
            "Gaming & Xbox"
        ],
        current_status={
            "microsoft_cloud_revenue": "$168B annually (up 23%)",
            "azure_revenue": "$75B annually (up 34%)",
            "ai_products": "100M+ monthly active users across Copilot apps",
            "microsoft_365_copilot": "Fastest new suite adoption, 100k+ deployments",
            "ai_agents": "3M agents created using SharePoint & Copilot Studio",
            "fabric_growth": "55% YoY, 25k+ customers",
            "commercial_bookings": "$100B+ for first time (up 30%)",
            "key_insight": "Leading AI infrastructure wave with compounding S-curves across silicon, systems, and models",
            "earnings_highlights": f"Recent earnings call highlights (truncated for brevity): {MICROSOFT_EARNINGS[:1000]}..."
        }
    )

    print(f"\n📋 Company Context:")
    print(f"   Name: Microsoft Corporation (MSFT)")
    print(f"   Business Areas: {len(microsoft_context.business_areas)}")
    print(f"   Earnings Context: {len(MICROSOFT_EARNINGS)} characters")
    print(f"\n   Key Metrics from Earnings:")
    for key, value in list(microsoft_context.current_status.items())[:6]:
        print(f"   • {key}: {value}")

    try:
        # Import required agents
        from deep_news_agent.agents.topic_agent import TopicAgent
        from deep_news_agent.agents.search_agent import SearchAgent
        from deep_news_agent.agents.ranking_agent import RankingAgent

        # Get API keys from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        tavily_api_key = os.getenv('TAVILY_API_KEY')

        if not openai_api_key or not tavily_api_key:
            print("❌ Error: OPENAI_API_KEY and TAVILY_API_KEY must be set in .env")
            return

        # Initialize agents
        print(f"\n🤖 Initializing AI agents...")
        topic_agent = TopicAgent(openai_api_key=openai_api_key, db_manager=db_manager)
        search_agent = SearchAgent(tavily_api_key=tavily_api_key, openai_api_key=openai_api_key)
        ranking_agent = RankingAgent(openai_api_key=openai_api_key)

        # Create pipeline config
        pipeline_config = PipelineConfig(
            max_iterations=max_iterations,
            max_questions_per_iteration=10,  # More questions for comprehensive research
            max_topics_in_memory=100,  # More topics for thorough analysis
            enable_earnings_retrieval=True,  # Use earnings context
            enable_fallback_strategies=True,
            parallel_processing=True  # Faster execution
        )

        # Initialize orchestrator
        print(f"🎯 Initializing orchestrator agent...")
        orchestrator = OrchestratorAgent(
            topic_agent=topic_agent,
            search_agent=search_agent,
            ranking_agent=ranking_agent,
            pipeline_config=pipeline_config,
            db_manager=db_manager
        )

        # Run the research pipeline
        print(f"\n{'='*80}")
        print(f"🚀 STARTING DEEP RESEARCH PIPELINE")
        print(f"{'='*80}\n")

        final_topics = await orchestrator.run_pipeline(microsoft_context)

        # Display results
        print(f"\n{'='*80}")
        print(f"✅ RESEARCH COMPLETE")
        print(f"{'='*80}")
        print(f"\n📊 Total Topics Discovered: {len(final_topics)}\n")

        if final_topics:
            print(f"🏆 Top 10 Topics by Importance:\n")
            for i, ranked_topic in enumerate(final_topics[:10], 1):
                topic = ranked_topic.topic
                print(f"{i}. {topic.name}")
                print(f"   📈 Final Score: {ranked_topic.final_score:.3f}")
                print(f"   ⚡ Urgency: {topic.urgency}")
                print(f"   💡 Business Impact: {topic.business_impact}")
                print(f"   📝 Description: {topic.description[:150]}...")
                print(f"   🔗 Sources: {len(topic.sources)} articles")

                if topic.subtopics:
                    print(f"   📂 Subtopics ({len(topic.subtopics)}):")
                    for subtopic in topic.subtopics[:3]:
                        if hasattr(subtopic, 'name'):
                            print(f"      - {subtopic.name}")
                        else:
                            print(f"      - {subtopic}")
                print()

            # Additional insights
            print(f"\n📈 Topic Categories Breakdown:")
            urgency_counts = {}
            for ranked_topic in final_topics:
                urgency = ranked_topic.topic.urgency
                urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1

            for urgency, count in sorted(urgency_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {urgency.upper()}: {count} topics")

            print(f"\n💾 All topics have been saved to Supabase database")
            print(f"   Company ID: Check companies table for 'MSFT'")
            print(f"   Topics can be queried via: /api/topics-by-interests?tickers=MSFT")

        return final_topics

    except Exception as e:
        print(f"\n❌ Error during research: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run deep research on Microsoft using earnings transcript")
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of research iterations (default: 3)"
    )

    args = parser.parse_args()

    print(f"\n🎯 Starting Microsoft deep research with {args.iterations} iterations...\n")
    asyncio.run(run_microsoft_research(max_iterations=args.iterations))
