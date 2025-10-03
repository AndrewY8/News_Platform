"""
Article Retriever Router Module - Updated to use Deep Research Agent System
Contains all article retrieval endpoints using OrchestratorAgent.
"""

import logging
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import sys

# Add parent directory to path for deep_research_agent imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from deep_news_agent.agents.orchestrator_agent import OrchestratorAgent
    from deep_news_agent.agents.topic_agent import TopicAgent
    from deep_news_agent.agents.search_agent import SearchAgent
    from deep_news_agent.agents.ranking_agent import RankingAgent
    from deep_news_agent.agents.interfaces import CompanyContext, PipelineConfig
    from deep_news_agent.config.api_keys import get_api_keys
    DEEP_RESEARCH_AVAILABLE = True
except Exception as e:
    DEEP_RESEARCH_AVAILABLE = False
    print(f"Warning: Deep Research Agent System not available in article retriever router: {e}")

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize deep research database manager (for reading pre-computed results)
research_db_manager = None

if DEEP_RESEARCH_AVAILABLE:
    try:
        from deep_news_agent.db.research_db_manager import ResearchDBManager

        # Initialize database manager for fetching pre-computed research
        supabase_url = os.getenv("SUPABASE_URL")
        # For read-only operations, anon key is fine. Service key can bypass RLS if needed.
        supabase_key = os.getenv("SUPABASE_KEY")

        if supabase_url and supabase_key:
            research_db_manager = ResearchDBManager(supabase_url, supabase_key)
            logger.info("✅ Article retriever router: Deep Research Database Manager initialized")
        else:
            logger.warning("⚠️ Supabase credentials not found - Deep Research database disabled")
            research_db_manager = None
    except Exception as e:
        logger.error(f"❌ Article retriever router: Failed to initialize Deep Research Database Manager: {e}", exc_info=True)
        research_db_manager = None
else:
    research_db_manager = None

# Pydantic Models for Articles
class ArticleModel(BaseModel):
    id: str
    headline: str
    summary: str
    url: str
    datetime: int
    category: Optional[str] = None
    sentiment_score: Optional[float] = None
    relevance_score: Optional[float] = None
    source: Optional[str] = None
    tags: Optional[str] = None

# Result transformation functions
def transform_db_articles_to_frontend(articles_data: List[Dict], company_name: str):
    """Transform database articles to frontend-compatible format"""
    articles = []

    if not articles_data:
        return articles

    for article_data in articles_data:
        try:
            # Use article ID from database
            article_id = str(article_data.get('id', hashlib.md5(str(article_data).encode()).hexdigest()[:16]))

            # Build tags from company and topic
            tags = [company_name]
            if article_data.get('topic_name'):
                tags.append(article_data['topic_name'])

            # Extract content preview
            content = article_data.get('content', '')
            title = article_data.get('title', 'Untitled Article')
            preview = content[:200] + "..." if len(content) > 200 else content

            article = {
                "id": article_id,
                "date": format_article_date(article_data.get('published_date')),
                "title": title,
                "source": article_data.get('source', 'Unknown'),
                "preview": preview,
                "sentiment": determine_sentiment_from_score(article_data.get('relevance_score')),
                "tags": tags,
                "url": article_data.get('url'),  # Actual article URL!
                "relevance_score": article_data.get('relevance_score', 0.5),
                "category": "News"
            }
            articles.append(article)

        except Exception as e:
            logger.error(f"Error transforming database article: {e}", exc_info=True)
            continue

    return articles

def determine_sentiment_from_score(score):
    """Determine sentiment from relevance score"""
    if not score:
        return 'neutral'
    if score >= 0.7:
        return 'positive'
    elif score <= 0.3:
        return 'negative'
    return 'neutral'

def transform_single_result_to_article(item, source_retriever):
    """Transform a single retrieval result to article format"""
    try:
        if isinstance(item, dict):
            # Generate unique ID using URL or content hash
            if item.get('id'):
                article_id = str(item['id'])
            elif item.get('url'):
                article_id = hashlib.md5(item['url'].encode()).hexdigest()[:16]
            else:
                # Use MD5 hash of the entire item for uniqueness
                article_id = hashlib.md5(str(item).encode()).hexdigest()[:16]

            return {
                "id": article_id,
                "date": format_article_date(item.get('published_date') or item.get('date') or item.get('timestamp')),
                "title": item.get('title') or item.get('headline') or 'Untitled Article',
                "source": item.get('source') or source_retriever,
                "preview": item.get('summary') or item.get('description') or item.get('content', '')[:200] + "...",
                "sentiment": determine_sentiment(item.get('sentiment')),
                "tags": extract_tags_from_item(item),
                "url": item.get('url') or item.get('link'),
                "relevance_score": item.get('relevance_score') or 0.5,
                "category": item.get('category') or 'General'
            }
        elif isinstance(item, str):
            # Generate unique ID for string items
            article_id = hashlib.md5(item.encode()).hexdigest()[:16]
            return {
                "id": article_id,
                "date": "Today",
                "title": item[:100] + "..." if len(item) > 100 else item,
                "source": source_retriever,
                "preview": item,
                "sentiment": 'neutral',
                "tags": [],
                "url": None,
                "relevance_score": 0.3,
                "category": 'General'
            }
    except Exception as e:
        logger.error(f"Error transforming item to article: {e}")
        return None

def format_article_date(date_input):
    """Format various date inputs to frontend-compatible format"""
    if not date_input:
        return "Today"
    try:
        if isinstance(date_input, str):
            from dateutil import parser
            date_obj = parser.parse(date_input)
        else:
            date_obj = date_input

        now = datetime.now()
        diff = now - date_obj

        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return date_obj.strftime("%b %d")
    except:
        return "Today"

def determine_sentiment(sentiment_input):
    """Determine sentiment from various inputs"""
    if not sentiment_input:
        return 'neutral'

    if isinstance(sentiment_input, (int, float)):
        if sentiment_input > 0.1:
            return 'positive'
        elif sentiment_input < -0.1:
            return 'negative'
        else:
            return 'neutral'

    sentiment_str = str(sentiment_input).lower()
    if 'positive' in sentiment_str or 'bullish' in sentiment_str:
        return 'positive'
    elif 'negative' in sentiment_str or 'bearish' in sentiment_str:
        return 'negative'
    else:
        return 'neutral'

def extract_tags_from_item(item):
    """Extract tags from various item formats"""
    tags = []
    for field in ['tags', 'keywords', 'topics', 'symbols']:
        if field in item and item[field]:
            if isinstance(item[field], list):
                tags.extend([str(tag) for tag in item[field]])
            else:
                tags.append(str(item[field]))
    return list(set(tags))

def get_fallback_articles():
    """Fallback articles when news agent is not available"""
    return [
        {
            "id": "fallback-1",
            "date": "Today",
            "title": "Market Update: Tech Stocks Rally on Strong Earnings",
            "source": "Financial Times",
            "preview": "Technology stocks led a broad market rally as major companies reported stronger-than-expected quarterly results...",
            "sentiment": "positive",
            "tags": ["AAPL", "MSFT", "NVDA"],
            "url": "#",
            "relevance_score": 0.9,
            "category": "Technology"
        },
        {
            "id": "fallback-2",
            "date": "Today",
            "title": "Federal Reserve Signals Potential Rate Cut",
            "source": "Reuters",
            "preview": "The Federal Reserve indicated it may consider cutting interest rates in the coming months...",
            "sentiment": "positive",
            "tags": ["MACRO", "FED"],
            "url": "#",
            "relevance_score": 0.8,
            "category": "Economy"
        }
    ]

# Article Route Functions
async def get_personalized_articles_handler(db: Session, Article, tickers: Optional[str] = None):
    """Get personalized articles from pre-computed deep research database"""
    try:
        # Build company context based on tickers if provided
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
            if not ticker_list:
                return JSONResponse(content=get_fallback_articles())

            # Use first ticker as primary company
            primary_ticker = ticker_list[0]
            logger.info(f"Fetching pre-computed research for ticker: {primary_ticker}")

            if research_db_manager:
                # Fetch actual articles from database (not just topics)
                articles_data = research_db_manager.get_company_articles(
                    company_name=primary_ticker,
                    limit=20
                )

                if articles_data:
                    # Transform database articles to frontend format
                    articles = transform_db_articles_to_frontend(articles_data, primary_ticker)
                    logger.info(f"Retrieved {len(articles)} pre-computed articles for {primary_ticker}")
                    return JSONResponse(content=articles)
                else:
                    logger.info(f"No pre-computed research found for {primary_ticker}, returning fallback")
                    return JSONResponse(content=get_fallback_articles())
            else:
                logger.warning("Research database manager not available, using fallback")
                return JSONResponse(content=get_fallback_articles())
        else:
            return JSONResponse(content=get_fallback_articles())

    except Exception as e:
        logger.error(f"Error getting personalized articles: {e}", exc_info=True)
        return JSONResponse(content=get_fallback_articles())

async def get_top_articles_handler(db: Session, Article):
    """Get top articles - returns fallback for now"""
    try:
        # For top articles, we can return fallback or implement a general market research
        # Deep research agent is designed for company-specific research
        logger.info("Top articles requested - returning fallback")
        return JSONResponse(content=get_fallback_articles())

    except Exception as e:
        logger.error(f"Error getting top articles: {e}")
        return JSONResponse(content=get_fallback_articles())

async def search_articles_handler(query: str, db: Session, Article):
    """Search articles - returns fallback for now"""
    try:
        # For search, we can return fallback or implement query-based research
        # Deep research agent is optimized for company-specific research
        logger.info(f"Article search requested for: {query} - returning fallback")
        return JSONResponse(content=get_fallback_articles())

    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        return JSONResponse(content=[])

# Function to add routes to FastAPI app
def add_article_retrieval_routes(app, shared_limiter, get_db, Article):
    """Add article retrieval routes to the FastAPI app"""

    @app.get("/api/articles")
    @shared_limiter.limit("30/minute")
    async def get_personalized_articles(request: Request, tickers: Optional[str] = None, db: Session = Depends(get_db)):
        return await get_personalized_articles_handler(db, Article, tickers)

    @app.get("/api/articles/top")
    @shared_limiter.limit("30/minute")
    async def get_top_articles(request: Request, db: Session = Depends(get_db)):
        return await get_top_articles_handler(db, Article)

    @app.get("/api/articles/search")
    @shared_limiter.limit("20/minute")
    async def search_articles(q: str, request: Request, db: Session = Depends(get_db)):
        return await search_articles_handler(q, db, Article)

    logger.info("Article retrieval routes added successfully")