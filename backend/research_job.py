"""
Background job to run deep research for companies and store results in database
This should be run periodically (e.g., via cron, scheduler, or background worker)
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_news_agent.agents.orchestrator_agent import OrchestratorAgent
from deep_news_agent.agents.topic_agent import TopicAgent
from deep_news_agent.agents.search_agent import SearchAgent
from deep_news_agent.agents.ranking_agent import RankingAgent
from deep_news_agent.agents.interfaces import CompanyContext, PipelineConfig
from deep_news_agent.db.research_db_manager import ResearchDBManager
from deep_news_agent.config.api_keys import get_api_keys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Companies to research (can be loaded from config/database)
COMPANIES_TO_RESEARCH = [
    # {"ticker": "AAPL", "name": "Apple Inc.", "industry": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "industry": "Technology"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "industry": "Technology"},
    # {"ticker": "AMZN", "name": "Amazon.com Inc.", "industry": "E-commerce"},
    # {"ticker": "NVDA", "name": "NVIDIA Corporation", "industry": "Technology"},
    # {"ticker": "TSLA", "name": "Tesla Inc.", "industry": "Automotive"},
    # {"ticker": "META", "name": "Meta Platforms Inc.", "industry": "Technology"},
    # {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "industry": "Finance"},
]


async def run_research_for_company(
    company_info: dict,
    research_agent: OrchestratorAgent,
    db_manager: ResearchDBManager
) -> bool:
    """Run deep research for a single company and store in database"""
    try:
        logger.info(f"Starting research for {company_info['name']} ({company_info['ticker']})")

        # Create company context
        company_context = CompanyContext(
            name=company_info['ticker'],
            ticker=company_info['ticker'],
            business_areas=["Technology", "Finance", "Markets"],  # Can enhance
            current_status={},
            industry=company_info.get('industry', 'Unknown')
        )

        # Run research pipeline
        ranked_topics = await research_agent.run_pipeline(company_context)

        logger.info(f"✅ Research completed for {company_info['ticker']}: {len(ranked_topics)} topics found")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to research {company_info['ticker']}: {e}", exc_info=True)
        return False


async def main():
    """Main research job that processes all companies"""
    logger.info("=" * 80)
    logger.info("Starting Deep Research Background Job")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 80)

    try:
        # Get API keys
        api_keys = get_api_keys()
        openai_key = api_keys.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        tavily_key = api_keys.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        # Use SERVICE_KEY for background jobs to bypass RLS
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        # Validate required credentials
        if not openai_key:
            logger.error("OPENAI_API_KEY not found in environment")
            return
        if not tavily_key:
            logger.error("TAVILY_API_KEY not found in environment")
            return
        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials not found in environment")
            return

        # Initialize database manager
        db_manager = ResearchDBManager(supabase_url, supabase_key)
        logger.info("✅ Database manager initialized")

        # Initialize agents
        topic_agent = TopicAgent(openai_api_key=openai_key, db_manager=db_manager)
        search_agent = SearchAgent(tavily_api_key=tavily_key, openai_api_key=openai_key)
        ranking_agent = RankingAgent(openai_api_key=openai_key)

        # Initialize orchestrator
        pipeline_config = PipelineConfig(
            max_iterations=2,  # Faster research for testing (change to 5 for full depth)
            max_questions_per_iteration=5,  # Reduced for speed
            enable_earnings_retrieval=False  # Disabled for faster research
        )

        research_agent = OrchestratorAgent(
            topic_agent=topic_agent,
            search_agent=search_agent,
            ranking_agent=ranking_agent,
            pipeline_config=pipeline_config,
            db_manager=db_manager
        )
        logger.info("✅ Research agent initialized")

        # Process each company
        success_count = 0
        failure_count = 0

        for company_info in COMPANIES_TO_RESEARCH:
            success = await run_research_for_company(company_info, research_agent, db_manager)
            if success:
                success_count += 1
            else:
                failure_count += 1

            # Small delay between companies to avoid rate limits
            await asyncio.sleep(2)

        # Summary
        logger.info("=" * 80)
        logger.info("Research Job Completed")
        logger.info(f"Total companies: {len(COMPANIES_TO_RESEARCH)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {failure_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Research job failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
