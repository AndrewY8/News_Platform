"""
Article Retriever Router Module - Updated to use News Agent System
Contains all article retrieval endpoints using PlannerAgent.
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

# Add parent directory to path for news_agent imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from news_agent.agent import PlannerAgent
    from news_agent.aggregator.aggregator import AggregatorAgent
    NEWS_AGENT_AVAILABLE = True
except Exception as e:
    NEWS_AGENT_AVAILABLE = False
    print(f"Warning: News Agent System not available in article retriever router: {e}")

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize news agent system
news_agent = None
aggregator_agent = None

if NEWS_AGENT_AVAILABLE:
    try:
        news_agent = PlannerAgent(max_concurrent_retrievers=3)
        aggregator_agent = AggregatorAgent()
        logger.info("Article retriever router: News Agent System initialized")
    except Exception as e:
        logger.error(f"Article retriever router: Failed to initialize News Agent System: {e}", exc_info=True)
        news_agent = None
        aggregator_agent = None

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
def transform_agent_results_to_articles(agent_results):
    """Transform news agent results to frontend-compatible article format"""
    articles = []

    if not agent_results or not isinstance(agent_results, list):
        return articles

    for result in agent_results:
        if result.get('status') != 'success' or not result.get('results'):
            continue

        retriever_name = result.get('retriever', 'Unknown')
        results = result.get('results', [])

        for item in results:
            article = transform_single_result_to_article(item, retriever_name)
            if article:
                articles.append(article)

    return articles

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
    """Get personalized articles using news agent system"""
    try:
        # Build query based on tickers if provided
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
            if ticker_list:
                query = f"latest news and financial updates about {', '.join(ticker_list)}"
                logger.info(f"Personalized query with tickers: {query}")
            else:
                query = "latest financial news market updates"
        else:
            query = "latest financial news market updates"

        if NEWS_AGENT_AVAILABLE and news_agent:
            agent_results = await news_agent.run_async(query)
            articles = transform_agent_results_to_articles(agent_results)
        else:
            articles = get_fallback_articles()

        return JSONResponse(content=articles[:10])

    except Exception as e:
        logger.error(f"Error getting personalized articles: {e}")
        return JSONResponse(content=get_fallback_articles())

async def get_top_articles_handler(db: Session, Article):
    """Get top articles using news agent system"""
    try:
        top_query = "breaking news financial markets today"

        if NEWS_AGENT_AVAILABLE and news_agent:
            agent_results = await news_agent.run_async(top_query)
            articles = transform_agent_results_to_articles(agent_results)
        else:
            articles = get_fallback_articles()

        return JSONResponse(content=articles[:15])

    except Exception as e:
        logger.error(f"Error getting top articles: {e}")
        return JSONResponse(content=get_fallback_articles())

async def search_articles_handler(query: str, db: Session, Article):
    """Search articles using news agent system"""
    try:
        if NEWS_AGENT_AVAILABLE and news_agent:
            agent_results = await news_agent.run_async(query)
            articles = transform_agent_results_to_articles(agent_results)
        else:
            articles = get_fallback_articles()

        return JSONResponse(content=articles[:20])

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