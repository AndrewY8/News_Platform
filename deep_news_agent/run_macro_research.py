"""
Run Macro/Political News Research

This script runs the deep research pipeline for macro and political topics.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from deep_news_agent.agents.orchestrator_agent import OrchestratorAgent
from deep_news_agent.agents.macro_interfaces import (
    MacroCategory,
    get_all_macro_contexts,
    get_macro_context_by_category
)
from deep_news_agent.db.research_db_manager import ResearchDBManager

# Load environment from root directory
load_dotenv(Path(__file__).parent.parent / '.env')


async def run_macro_research(categories=None, max_iterations=3):
    """
    Run macro research for specified categories

    Args:
        categories: List of MacroCategory enums, or None for all categories
        max_iterations: Number of research iterations
    """

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    # Use service key for backend operations to bypass RLS policies
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) must be set in .env")
        return

    # Initialize database manager
    db_manager = ResearchDBManager(supabase_url, supabase_key)

    # Get contexts to research
    if categories is None:
        contexts = get_all_macro_contexts()
        print(f"🔍 Running research for ALL {len(contexts)} macro categories\n")
    else:
        contexts = [get_macro_context_by_category(cat) for cat in categories]
        print(f"🔍 Running research for {len(contexts)} selected categories\n")

    # Run research for each context
    results = []
    for i, context in enumerate(contexts, 1):
        print(f"\n{'='*80}")
        print(f"📊 [{i}/{len(contexts)}] Researching: {context.get_display_name()}")
        print(f"Category: {context.category.value}")
        print(f"Type: {context.topic_type}")
        print(f"Sector: {context.sector}")
        print(f"{'='*80}\n")

        try:
            # Import required agents and config
            from deep_news_agent.agents.topic_agent import TopicAgent
            from deep_news_agent.agents.search_agent import SearchAgent
            from deep_news_agent.agents.ranking_agent import RankingAgent
            from deep_news_agent.agents.interfaces import PipelineConfig

            # Get API keys from environment
            openai_api_key = os.getenv('OPENAI_API_KEY')
            tavily_api_key = os.getenv('TAVILY_API_KEY')

            # Initialize agents with db_manager
            topic_agent = TopicAgent(openai_api_key=openai_api_key, db_manager=db_manager)
            search_agent = SearchAgent(tavily_api_key=tavily_api_key, openai_api_key=openai_api_key)
            ranking_agent = RankingAgent(openai_api_key=openai_api_key)  # RankingAgent doesn't use db_manager

            # Create pipeline config
            pipeline_config = PipelineConfig(
                max_iterations=max_iterations,
                max_questions_per_iteration=8,
                max_topics_in_memory=50,
                enable_earnings_retrieval=False,  # Macro topics don't use earnings
                enable_fallback_strategies=True,
                parallel_processing=False
            )

            # Initialize orchestrator
            orchestrator = OrchestratorAgent(
                topic_agent=topic_agent,
                search_agent=search_agent,
                ranking_agent=ranking_agent,
                pipeline_config=pipeline_config,
                db_manager=db_manager
            )

            # Run the research pipeline
            print(f"🚀 Starting {max_iterations}-iteration research pipeline...")
            final_topics = await orchestrator.run_pipeline(context)

            print(f"\n✅ Research complete for {context.get_display_name()}")
            print(f"   Found {len(final_topics)} topics")

            # Display top topics
            if final_topics:
                print(f"\n   Top Topics:")
                for j, ranked_topic in enumerate(final_topics[:5], 1):
                    topic = ranked_topic.topic
                    print(f"   {j}. {topic.name}")
                    print(f"      Urgency: {topic.urgency} | Score: {ranked_topic.final_score:.3f}")
                    print(f"      {topic.description[:100]}...")

            results.append({
                "context": context,
                "topics": final_topics,
                "topic_count": len(final_topics)
            })

        except Exception as e:
            print(f"❌ Error researching {context.get_display_name()}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # Summary
    print(f"\n\n{'='*80}")
    print(f"📈 RESEARCH SUMMARY")
    print(f"{'='*80}")
    total_topics = sum(r['topic_count'] for r in results)
    print(f"Total categories researched: {len(results)}")
    print(f"Total topics extracted: {total_topics}")
    print(f"\nBreakdown by category:")
    for result in results:
        context = result['context']
        count = result['topic_count']
        print(f"  • {context.get_display_name()}: {count} topics")

    return results


async def run_single_category(category: MacroCategory, max_iterations=3):
    """Run research for a single macro category"""
    return await run_macro_research(categories=[category], max_iterations=max_iterations)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run macro/political news research")
    parser.add_argument(
        "--category",
        type=str,
        choices=[cat.value for cat in MacroCategory],
        help="Specific category to research (default: all)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of research iterations (default: 3)"
    )

    args = parser.parse_args()

    # Determine which categories to run
    if args.category:
        category = MacroCategory(args.category)
        print(f"Running research for category: {category.value}")
        asyncio.run(run_single_category(category, max_iterations=args.iterations))
    else:
        print("Running research for ALL categories")
        asyncio.run(run_macro_research(max_iterations=args.iterations))
