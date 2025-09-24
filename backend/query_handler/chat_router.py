"""
Chat Router Module - Updated to use News Agent System
Contains all chat/search related FastAPI endpoints using PlannerAgent and AggregatorAgent.
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
import google.generativeai as genai
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
    print(f"Warning: News Agent System not available in chat router: {e}")

logger = logging.getLogger(__name__)

# Initialize rate limiter (will use the same one from main app)
limiter = Limiter(key_func=get_remote_address)

# Initialize news agent system
news_agent = None
aggregator_agent = None

if NEWS_AGENT_AVAILABLE:
    try:
        news_agent = PlannerAgent(max_concurrent_retrievers=3)
        from news_agent.aggregator.config import AggregatorConfig
        aggregator_config = AggregatorConfig.from_env()
        aggregator_agent = AggregatorAgent(config=aggregator_config)
        logger.info("Chat router: News Agent System initialized")
    except Exception as e:
        logger.error(f"Chat router: Failed to initialize News Agent System: {e}")
        news_agent = None
        aggregator_agent = None

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Pydantic Models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List[Dict]] = []

class EnhancedSearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    use_agent: bool = True
    limit: int = 10

class ChatHistoryModel(BaseModel):
    id: str
    query: str
    response: Optional[str] = None
    timestamp: datetime

# Result transformation functions (same as in main app.py)
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
            # Handle Tavily format which uses 'href' and 'body'
            url = item.get('url') or item.get('link') or item.get('href')
            content = item.get('content') or item.get('body', '')
            title = item.get('title') or item.get('headline')

            # If no title, extract from content or URL
            if not title:
                if content:
                    # Extract title from first sentence or first 100 chars
                    title = content.split('.')[0][:100] if content else 'Untitled Article'
                elif url:
                    # Extract title from URL
                    title = url.split('/')[-1].replace('-', ' ').replace('_', ' ')[:100]
                else:
                    title = 'Untitled Article'

            # Use actual source name from the article, not the retriever name
            actual_source = item.get('source')
            if not actual_source or actual_source == source_retriever:
                # If no source or source is just the retriever name, try to extract from URL
                if url:
                    actual_source = url.split("//")[-1].split("/")[0].replace("www.", "").title()
                else:
                    actual_source = source_retriever

            # Clean and format the preview content
            preview_text = item.get('summary') or item.get('description') or content or ""
            if preview_text:
                # Remove markdown formatting and clean up the text
                preview_text = preview_text.strip()
                # Remove leading dots, hashes, and other markdown artifacts
                preview_text = preview_text.lstrip('...').lstrip('#').lstrip('*').lstrip('-').strip()
                # Remove multiple spaces and newlines
                preview_text = ' '.join(preview_text.split())
                # Ensure it's not too long
                if len(preview_text) > 200:
                    preview_text = preview_text[:200].rsplit(' ', 1)[0] + "..."
                # If it's empty after cleaning, use fallback
                if not preview_text or len(preview_text) < 10:
                    preview_text = "Click to read full article..."
            else:
                preview_text = "Click to read full article..."

            return {
                "id": item.get('id') or f"{source_retriever}-{hash(str(item))}"[:16],
                "date": format_article_date(item.get('published_date') or item.get('date') or item.get('timestamp')),
                "title": title,
                "source": actual_source,
                "preview": preview_text,
                "sentiment": determine_sentiment(item.get('sentiment')),
                "tags": extract_tags_from_item(item),
                "url": url,
                "relevance_score": item.get('relevance_score') or item.get('score') or 0.5,
                "category": item.get('category') or 'General'
            }
        elif isinstance(item, str):
            return {
                "id": f"{source_retriever}-{hash(item)}"[:16],
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

def create_findings_summary(agent_results, articles):
    """Create a summary of findings for Gemini"""
    if not agent_results:
        return "No results found."

    summary_parts = []

    if isinstance(agent_results, list):
        successful = [r for r in agent_results if r.get('status') == 'success']
        summary_parts.append(f"Searched {len(agent_results)} sources, {len(successful)} successful.")

        if successful:
            sources = [r.get('retriever', 'Unknown') for r in successful]
            summary_parts.append(f"Active sources: {', '.join(set(sources))}")

    summary_parts.append(f"Found {len(articles)} relevant articles.")

    if articles:
        sample_titles = [a['title'] for a in articles[:3]]
        summary_parts.append(f"Key articles: {'; '.join(sample_titles)}")

    return "\n".join(summary_parts)

# Chat Route Functions
async def chat_about_news(request: ChatRequest, db: Session, User, ChatHistory):
    """Enhanced chat using news agent system"""
    try:
        if not NEWS_AGENT_AVAILABLE or not news_agent:
            return JSONResponse(content={
                "response": "I apologize, but the news research system is currently unavailable. Please try again later.",
                "suggested_articles": []
            })

        logger.info(f"Chat request: {request.message}")

        # Use the PlannerAgent to research the query
        agent_results = await news_agent.run_async(request.message)

        # Transform results to articles
        suggested_articles = transform_agent_results_to_articles(agent_results)

        # Generate a response using Gemini based on the results
        try:
            findings_summary = create_findings_summary(agent_results, suggested_articles)

            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content([
                f"Based on the following news research findings for the user query '{request.message}', provide a helpful, conversational response. Focus on the key insights and mention that I've found relevant articles to review:\n\n{findings_summary}\n\nProvide a response as if you're a knowledgeable financial news assistant."
            ])

            ai_response = response.text

        except Exception as e:
            logger.error(f"Gemini response error: {e}")
            ai_response = f"I've researched your query about '{request.message}' and found several relevant articles. Please review the suggested articles below for the latest information."

        # Save chat history
        try:
            chat_entry = ChatHistory(
                id=f"chat-{int(time.time())}-{hash(request.message) % 10000}",
                user_id=str(request.user_id),
                query=request.message,
                response=ai_response,
                timestamp=datetime.utcnow()
            )
            db.add(chat_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")

        return JSONResponse(content={
            "response": ai_response,
            "suggested_articles": suggested_articles[:5]
        })

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return JSONResponse(content={
            "response": "I encountered an error while researching your query. Please try rephrasing your question or try again later.",
            "suggested_articles": []
        })

async def enhanced_search_handler(request: EnhancedSearchRequest, db: Session):
    """Enhanced search using the news agent system"""
    try:
        if not NEWS_AGENT_AVAILABLE or not news_agent:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "News agent system not available",
                    "articles": [],
                    "search_method": "unavailable",
                    "sources_used": [],
                    "total_found": 0
                }
            )

        logger.info(f"Enhanced search request: {request.query}")

        # Use the PlannerAgent to get results
        agent_results = await news_agent.run_async(request.query)

        # Transform results to frontend format
        articles = transform_agent_results_to_articles(agent_results)

        # Limit results if needed
        if request.limit and len(articles) > request.limit:
            articles = articles[:request.limit]

        # Extract sources used
        sources_used = []
        if isinstance(agent_results, list):
            sources_used = [result.get('retriever', 'Unknown') for result in agent_results if result.get('status') == 'success']

        return JSONResponse(content={
            "success": True,
            "articles": articles,
            "search_method": "news_agent_planner",
            "sources_used": list(set(sources_used)),
            "total_found": len(articles)
        })

    except Exception as e:
        logger.error(f"Enhanced search error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "articles": [],
                "search_method": "error",
                "sources_used": [],
                "total_found": 0
            }
        )

# Function to add routes to FastAPI app
def add_chat_routes(app, shared_limiter, get_db, User, ChatHistory):
    """Add chat routes to the FastAPI app"""

    @app.post("/api/chat")
    @shared_limiter.limit("20/minute")
    async def chat_endpoint(request: Request, chat_request: ChatRequest, db: Session = Depends(get_db)):
        return await chat_about_news(chat_request, db, User, ChatHistory)

    @app.post("/api/search/enhanced")
    @shared_limiter.limit("10/minute")
    async def enhanced_search(request: Request, search_request: EnhancedSearchRequest, db: Session = Depends(get_db)):
        return await enhanced_search_handler(search_request, db)

    logger.info("Chat routes added successfully")