import os
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from fastapi import FastAPI, HTTPException, Request, Depends, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer
import requests
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    Float,
    DateTime,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from news_agent.integration.planner_aggregator import create_enhanced_planner
from newsapi import NewsApiClient

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception as e:
    print(f"Warning: yfinance not available: {e}")
    YFINANCE_AVAILABLE = False
    yf = None
    
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Simple auth placeholder (auth.py not available)
def get_current_user_optional():
    """Optional auth placeholder"""
    return None
# Ticker validation functions (simplified versions)
def validate_ticker_list(tickers):
    """Simple ticker validation - can be enhanced later"""
    if not tickers or not isinstance(tickers, list):
        return []
    return [ticker.upper().strip() for ticker in tickers if ticker and isinstance(ticker, str)]

def get_ticker_suggestions(query):
    """Simple ticker suggestions - can be enhanced later"""
    return []

# Import Google Gemini for AI functionality
# Simple auth placeholder (auth.py not available)
def get_current_user_optional():
    """Optional auth placeholder"""
    return None
# Ticker validation functions (simplified versions)
def validate_ticker_list(tickers):
    """Simple ticker validation - can be enhanced later"""
    if not tickers or not isinstance(tickers, list):
        return []
    return [ticker.upper().strip() for ticker in tickers if ticker and isinstance(ticker, str)]

def get_ticker_suggestions(query):
    """Simple ticker suggestions - can be enhanced later"""
    return []

# Import Google Gemini for AI functionality
import google.generativeai as genai

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from news_agent.agent import PlannerAgent
    from news_agent.aggregator.aggregator import AggregatorAgent
    NEWS_AGENT_AVAILABLE = True
    print("✅ News Agent System available")
except Exception as e:
    NEWS_AGENT_AVAILABLE = False
    print(f"⚠️ News Agent System not available: {e}")
    NEWS_AGENT_AVAILABLE = False
    print(f"⚠️ News Agent System not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "1f96d48a73e24ad19d3e68449d982290")
newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

# OAuth configuration (imported from environment)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_news.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Initialize News Agent System
news_agent = None
aggregator_agent = None

if NEWS_AGENT_AVAILABLE:
    try:
        news_agent = PlannerAgent(max_concurrent_retrievers=3)
        from news_agent.aggregator.config import AggregatorConfig
        aggregator_config = AggregatorConfig.from_env()
        aggregator_agent = AggregatorAgent(config=aggregator_config)
        logger.info("🚀 News Agent System initialized successfully")
        news_agent = PlannerAgent(max_concurrent_retrievers=3)
        from news_agent.aggregator.config import AggregatorConfig
        aggregator_config = AggregatorConfig.from_env()
        aggregator_agent = AggregatorAgent(config=aggregator_config)
        logger.info("🚀 News Agent System initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize News Agent System: {e}")
        news_agent = None
        aggregator_agent = None
        logger.error(f"❌ Failed to initialize News Agent System: {e}")
        news_agent = None
        aggregator_agent = None


# Enhanced Models for OAuth
class User(Base):
    __tablename__ = "users"

    # Core fields
    id = Column(String, primary_key=True, index=True)  # OAuth provider ID
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    full_name = Column(String)

    # OAuth fields
    provider = Column(String, nullable=False)  # 'google', 'github'
    provider_id = Column(String, nullable=False)  # Provider's user ID
    avatar_url = Column(String)
    verified = Column(Boolean, default=False)

    # App-specific fields
    trades = Column(String, default="[]")  # JSON string of tickers
    preferences = Column(Text, default="{}")  # JSON string of user preferences
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    interactions = relationship("UserInteraction", back_populates="user")


class Article(Base):
    __tablename__ = "articles"
    id = Column(String, primary_key=True, index=True)
    headline = Column(String)
    summary = Column(String)
    url = Column(String)
    datetime = Column(Integer)
    saved = Column(Boolean, default=False)
    removed = Column(Boolean, default=False)

    # New fields for personalization
    category = Column(String)
    sentiment_score = Column(Float)
    relevance_score = Column(Float)
    source = Column(String)
    tags = Column(Text)  # JSON string of tags
    content_analysis = Column(Text)  # JSON string of analysis

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False)
    action = Column(String, nullable=False)  # 'view', 'save', 'click', etc.
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False)
    action = Column(String, nullable=False)  # 'view', 'save', 'click', etc.
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="interactions")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


# Pydantic models

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Configure Gemini
print(os.getenv("GEMINI_API_KEY"))
print(os.getenv("GEMINI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# FastAPI app setup
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Session middleware for OAuth state management
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-super-secure-secret-key"),
)

# Enhanced CORS with environment-based origins
cors_origins = ["http://localhost:3000", "http://localhost:3001", "http://3.92.79.88:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Required for cookies/sessions
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Accept-Language", "Content-Language"],
)


# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    return response

# Database dependency
# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    return response

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List[Dict]] = []

class EnhancedSearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    use_agent: bool = True
    limit: int = 10

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

        # Handle different result formats from different retrievers
        for item in results:
            article = transform_single_result_to_article(item, retriever_name)
            if article:
                articles.append(article)

    return articles

def transform_single_result_to_article(item, source_retriever):
    """Transform a single retrieval result to article format"""
    try:
        # Handle different item formats
        if isinstance(item, dict):
            return {
                "id": item.get('id') or f"{source_retriever}-{hash(str(item))}"[:16],
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
            # Try parsing various date formats
            from dateutil import parser
            date_obj = parser.parse(date_input)
        else:
            date_obj = date_input

        # Return relative time
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

    # Try different tag fields
    for field in ['tags', 'keywords', 'topics', 'symbols']:
        if field in item and item[field]:
            if isinstance(item[field], list):
                tags.extend([str(tag) for tag in item[field]])
# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List[Dict]] = []

class EnhancedSearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    use_agent: bool = True
    limit: int = 10

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

        # Handle different result formats from different retrievers
        for item in results:
            article = transform_single_result_to_article(item, retriever_name)
            if article:
                articles.append(article)

    return articles

def transform_single_result_to_article(item, source_retriever):
    """Transform a single retrieval result to article format"""
    try:
        # Handle different item formats
        if isinstance(item, dict):
            return {
                "id": item.get('id') or f"{source_retriever}-{hash(str(item))}"[:16],
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
            # Try parsing various date formats
            from dateutil import parser
            date_obj = parser.parse(date_input)
        else:
            date_obj = date_input

        # Return relative time
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

    # Try different tag fields
    for field in ['tags', 'keywords', 'topics', 'symbols']:
        if field in item and item[field]:
            if isinstance(item[field], list):
                tags.extend([str(tag) for tag in item[field]])
            else:
                tags.append(str(item[field]))

    return list(set(tags))  # Remove duplicates

# API Endpoints

# Note: Enhanced search and chat endpoints are now handled by the chat_router

def create_findings_summary(agent_results, articles):
    """Create a summary of findings for Gemini"""
    if not agent_results:
        return "No results found."

    summary_parts = []

    # Count successful retrievers
    if isinstance(agent_results, list):
        successful = [r for r in agent_results if r.get('status') == 'success']
        failed = [r for r in agent_results if r.get('status') == 'error']

        summary_parts.append(f"Searched {len(agent_results)} sources, {len(successful)} successful.")

        if successful:
            sources = [r.get('retriever', 'Unknown') for r in successful]
            summary_parts.append(f"Active sources: {', '.join(set(sources))}")

    summary_parts.append(f"Found {len(articles)} relevant articles.")

    # Add sample titles
    if articles:
        sample_titles = [a['title'] for a in articles[:3]]
        summary_parts.append(f"Key articles: {'; '.join(sample_titles)}")

    return "\n".join(summary_parts)

# Import handler routers
try:
    from query_handler.chat_router import add_chat_routes
    from query_handler.article_retriever_router import add_article_retrieval_routes
    from query_handler.chat_history_routes import add_chat_history_routes
    from ticker_handler.ticker_routes import add_ticker_routes
    from db_handler.user_routes import add_user_routes
    HANDLERS_AVAILABLE = True
except Exception as e:
    HANDLERS_AVAILABLE = False
    logger.warning(f"Handler modules not available: {e}")

# Re-enable handlers after fixing parameter ordering
HANDLERS_AVAILABLE = True
logger.info("✅ Using handler routes with fixed parameter ordering")

# Add all routes from handlers if available
if HANDLERS_AVAILABLE:
    try:
        add_chat_routes(app, limiter, get_db, User, ChatHistory)
        add_article_retrieval_routes(app, limiter, get_db, Article)
        add_chat_history_routes(app, limiter, get_db, ChatHistory)
        add_ticker_routes(app, limiter, get_db, User)
        add_user_routes(app, limiter, get_db, User, Article)
        logger.info("✅ All handler routes loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load handler routes: {e}")
        HANDLERS_AVAILABLE = False

# API Endpoints

# Note: Enhanced search and chat endpoints are now handled by the chat_router

def create_findings_summary(agent_results, articles):
    """Create a summary of findings for Gemini"""
    if not agent_results:
        return "No results found."

    summary_parts = []

    # Count successful retrievers
    if isinstance(agent_results, list):
        successful = [r for r in agent_results if r.get('status') == 'success']
        failed = [r for r in agent_results if r.get('status') == 'error']

        summary_parts.append(f"Searched {len(agent_results)} sources, {len(successful)} successful.")

        if successful:
            sources = [r.get('retriever', 'Unknown') for r in successful]
            summary_parts.append(f"Active sources: {', '.join(set(sources))}")

    summary_parts.append(f"Found {len(articles)} relevant articles.")

    # Add sample titles
    if articles:
        sample_titles = [a['title'] for a in articles[:3]]
        summary_parts.append(f"Key articles: {'; '.join(sample_titles)}")

    return "\n".join(summary_parts)

# Import handler routers
try:
    from query_handler.chat_router import add_chat_routes
    from query_handler.article_retriever_router import add_article_retrieval_routes
    from query_handler.chat_history_routes import add_chat_history_routes
    from ticker_handler.ticker_routes import add_ticker_routes
    from db_handler.user_routes import add_user_routes
    HANDLERS_AVAILABLE = True
except Exception as e:
    HANDLERS_AVAILABLE = False
    logger.warning(f"Handler modules not available: {e}")

# Re-enable handlers after fixing parameter ordering
HANDLERS_AVAILABLE = True
logger.info("✅ Using handler routes with fixed parameter ordering")

# Add all routes from handlers if available
if HANDLERS_AVAILABLE:
    try:
        add_chat_routes(app, limiter, get_db, User, ChatHistory)
        add_article_retrieval_routes(app, limiter, get_db, Article)
        add_chat_history_routes(app, limiter, get_db, ChatHistory)
        add_ticker_routes(app, limiter, get_db, User)
        add_user_routes(app, limiter, get_db, User, Article)
        logger.info("✅ All handler routes loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load handler routes: {e}")
        HANDLERS_AVAILABLE = False

# Fallback routes when handlers are not available
if not HANDLERS_AVAILABLE:
    logger.info("⚠️ Loading fallback routes since handlers are not available")

    @app.get("/api/chat/history")
    @limiter.limit("10/minute")
    async def get_chat_history_fallback(request: Request, db: Session = Depends(get_db)):
        """Get chat history for user (fallback)"""
        try:
            history = db.query(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(50).all()
            return JSONResponse(content=[
                {
                    "id": chat.id,
                    "query": chat.query,
                    "response": chat.response,
                    "timestamp": chat.timestamp.isoformat()
                }
                for chat in history
            ])
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return JSONResponse(content=[])
    @app.get("/api/chat/history")
    @limiter.limit("10/minute")
    async def get_chat_history_fallback(request: Request, db: Session = Depends(get_db)):
        """Get chat history for user (fallback)"""
        try:
            history = db.query(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(50).all()
            return JSONResponse(content=[
                {
                    "id": chat.id,
                    "query": chat.query,
                    "response": chat.response,
                    "timestamp": chat.timestamp.isoformat()
                }
                for chat in history
            ])
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return JSONResponse(content=[])

    @app.post("/api/chat/history")
    @limiter.limit("20/minute")
    async def save_chat_history_fallback(request: Request, db: Session = Depends(get_db)):
        """Save chat query to history (fallback)"""
        try:
            data = await request.json()
            chat_entry = ChatHistory(
                id=f"chat-{int(time.time())}-{hash(data.get('query', '')) % 10000}",
                user_id="1",
                query=data.get('query', ''),
                response=data.get('response', ''),
                timestamp=datetime.utcnow()
            )
            db.add(chat_entry)
            db.commit()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})
    @app.post("/api/chat/history")
    @limiter.limit("20/minute")
    async def save_chat_history_fallback(request: Request, db: Session = Depends(get_db)):
        """Save chat query to history (fallback)"""
        try:
            data = await request.json()
            chat_entry = ChatHistory(
                id=f"chat-{int(time.time())}-{hash(data.get('query', '')) % 10000}",
                user_id="1",
                query=data.get('query', ''),
                response=data.get('response', ''),
                timestamp=datetime.utcnow()
            )
            db.add(chat_entry)
            db.commit()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})

    @app.delete("/api/chat/history/{query_id}")
    @limiter.limit("10/minute")
    async def delete_chat_history_fallback(query_id: str, request: Request, db: Session = Depends(get_db)):
        """Delete chat history entry (fallback)"""
        try:
            chat_entry = db.query(ChatHistory).filter(ChatHistory.id == query_id).first()
            if chat_entry:
                db.delete(chat_entry)
                db.commit()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error deleting chat history: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})

    @app.get("/api/market/summary")
    @limiter.limit("30/minute")
    async def get_market_summary_fallback(tickers: str, request: Request):
        """Get market data for tickers (fallback)"""
        try:
            ticker_list = tickers.split(',')
            mock_data = {
                'AAPL': {'price': 175.20, 'change': 2.15, 'change_percent': 1.24},
                'MSFT': {'price': 378.85, 'change': -1.25, 'change_percent': -0.33},
                'NVDA': {'price': 821.67, 'change': 15.42, 'change_percent': 1.91},
                'TSLA': {'price': 195.33, 'change': -3.12, 'change_percent': -1.57},
                'AMZN': {'price': 152.74, 'change': 0.87, 'change_percent': 0.57},
                'GOOGL': {'price': 138.25, 'change': 1.34, 'change_percent': 0.98}
            }
            ticker_data = []
            for ticker in ticker_list:
                ticker = ticker.strip().upper()
                if ticker in mock_data:
                    data = mock_data[ticker]
                    ticker_data.append({
                        'symbol': ticker,
                        'current_price': data['price'],
                        'change': data['change'],
                        'change_percent': data['change_percent']
                    })
                else:
                    ticker_data.append({
                        'symbol': ticker,
                        'current_price': 100.0,
                        'change': 0.0,
                        'change_percent': 0.0
                    })
            return JSONResponse(content={'tickers': ticker_data})
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return JSONResponse(content={'tickers': []})

    @app.post("/api/user")
    @limiter.limit("10/minute")
    async def update_user_fallback(request: Request, db: Session = Depends(get_db)):
        """Update user preferences (fallback)"""
        try:
            data = await request.json()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})
    @app.delete("/api/chat/history/{query_id}")
    @limiter.limit("10/minute")
    async def delete_chat_history_fallback(query_id: str, request: Request, db: Session = Depends(get_db)):
        """Delete chat history entry (fallback)"""
        try:
            chat_entry = db.query(ChatHistory).filter(ChatHistory.id == query_id).first()
            if chat_entry:
                db.delete(chat_entry)
                db.commit()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error deleting chat history: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})

    @app.get("/api/market/summary")
    @limiter.limit("30/minute")
    async def get_market_summary_fallback(tickers: str, request: Request):
        """Get market data for tickers (fallback)"""
        try:
            ticker_list = tickers.split(',')
            mock_data = {
                'AAPL': {'price': 175.20, 'change': 2.15, 'change_percent': 1.24},
                'MSFT': {'price': 378.85, 'change': -1.25, 'change_percent': -0.33},
                'NVDA': {'price': 821.67, 'change': 15.42, 'change_percent': 1.91},
                'TSLA': {'price': 195.33, 'change': -3.12, 'change_percent': -1.57},
                'AMZN': {'price': 152.74, 'change': 0.87, 'change_percent': 0.57},
                'GOOGL': {'price': 138.25, 'change': 1.34, 'change_percent': 0.98}
            }
            ticker_data = []
            for ticker in ticker_list:
                ticker = ticker.strip().upper()
                if ticker in mock_data:
                    data = mock_data[ticker]
                    ticker_data.append({
                        'symbol': ticker,
                        'current_price': data['price'],
                        'change': data['change'],
                        'change_percent': data['change_percent']
                    })
                else:
                    ticker_data.append({
                        'symbol': ticker,
                        'current_price': 100.0,
                        'change': 0.0,
                        'change_percent': 0.0
                    })
            return JSONResponse(content={'tickers': ticker_data})
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return JSONResponse(content={'tickers': []})

    @app.post("/api/user")
    @limiter.limit("10/minute")
    async def update_user_fallback(request: Request, db: Session = Depends(get_db)):
        """Update user preferences (fallback)"""
        try:
            data = await request.json()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})

    @app.post("/api/articles/{article_id}/save")
    @limiter.limit("20/minute")
    async def save_article_fallback(article_id: str, request: Request, db: Session = Depends(get_db)):
        """Save an article (fallback)"""
        try:
            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.saved = True
                db.commit()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})

    @app.post("/api/articles/{article_id}/unsave")
    @limiter.limit("20/minute")
    async def unsave_article_fallback(article_id: str, request: Request, db: Session = Depends(get_db)):
        """Unsave an article (fallback)"""
        try:
            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.saved = False
                db.commit()
            return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error unsaving article: {e}")
            return JSONResponse(content={"success": False, "error": str(e)})

    @app.get("/api/articles/saved")
    @limiter.limit("30/minute")
    async def get_saved_articles_fallback(request: Request, db: Session = Depends(get_db)):
        """Get saved articles (fallback)"""
        try:
            saved = db.query(Article).filter(Article.saved == True).limit(20).all()
            articles = []
            for article in saved:
                articles.append({
                    "id": article.id,
                    "date": format_article_date(article.datetime),
                    "title": article.headline,
                    "source": article.source or 'Unknown',
                    "preview": article.summary or 'No preview available',
                    "sentiment": determine_sentiment(article.sentiment_score),
                    "tags": extract_tags_from_item({"tags": article.tags}) if article.tags else [],
                    "url": article.url,
                    "relevance_score": article.relevance_score or 0.5,
                    "category": article.category or 'General'
                })
            return JSONResponse(content=articles)
        except Exception as e:
            logger.error(f"Error getting saved articles: {e}")
            return JSONResponse(content=[])

# Additional aggregated search endpoint for advanced functionality
@app.post("/api/search/aggregated")
@limiter.limit("5/minute")
async def aggregated_search(request: EnhancedSearchRequest, req: Request, db: Session = Depends(get_db)):
    """Search using both agent and aggregator pipeline"""
    try:
        if not NEWS_AGENT_AVAILABLE or not news_agent:
            return JSONResponse(
                status_code=503,
                content={"error": "News agent system not available", "articles": []}
            )

        logger.info(f"Aggregated search request: {request.query}")

        # Step 1: Use PlannerAgent to get raw results
        agent_results = await news_agent.run_async(request.query)

        # Step 2: If aggregator is available, process through aggregation pipeline
        if aggregator_agent:
            try:
                # Convert agent results to aggregator input format
                content_chunks = convert_agent_results_to_chunks(agent_results)

                # Run through aggregator
                aggregated_output = await aggregator_agent.run_async(content_chunks)

                # Transform aggregated results back to articles
                articles = transform_aggregated_results_to_articles(aggregated_output)

                return JSONResponse(content={
                    "success": True,
                    "articles": articles[:request.limit],
                    "search_method": "agent_plus_aggregator",
                    "processing_details": {
                        "raw_results": len(agent_results) if isinstance(agent_results, list) else 0,
                        "aggregated_clusters": getattr(aggregated_output, 'clusters', []),
                        "final_articles": len(articles)
                    }
                })

            except Exception as e:
                logger.error(f"Aggregator processing failed, falling back to agent only: {e}")
                # Fall back to just agent results
                articles = transform_agent_results_to_articles(agent_results)

        else:
            # Just use agent results
            articles = transform_agent_results_to_articles(agent_results)

        return JSONResponse(content={
            "success": True,
            "articles": articles[:request.limit],
            "search_method": "agent_only",
            "total_found": len(articles)
        })
    except Exception as e:
        logger.error(f"Aggregated search error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "articles": []}
        )

def convert_agent_results_to_chunks(agent_results):
    """Convert agent results to format expected by aggregator"""
    chunks = []

    if not isinstance(agent_results, list):
        return chunks

    for result in agent_results:
        if result.get('status') != 'success' or not result.get('results'):
            continue

        retriever_name = result.get('retriever', 'Unknown')
        results = result.get('results', [])

        for item in results:
            if isinstance(item, dict):
                chunk = {
                    'content': item.get('summary') or item.get('description') or str(item),
                    'title': item.get('title') or item.get('headline'),
                    'url': item.get('url') or item.get('link'),
                    'source': retriever_name,
                    'metadata': item
                }
                chunks.append(chunk)

    return chunks

def convert_agent_results_to_chunks(agent_results):
    """Convert agent results to format expected by aggregator"""
    chunks = []

    if not isinstance(agent_results, list):
        return chunks

    for result in agent_results:
        if result.get('status') != 'success' or not result.get('results'):
            continue

        retriever_name = result.get('retriever', 'Unknown')
        results = result.get('results', [])

        for item in results:
            if isinstance(item, dict):
                chunk = {
                    'content': item.get('summary') or item.get('description') or str(item),
                    'title': item.get('title') or item.get('headline'),
                    'url': item.get('url') or item.get('link'),
                    'source': retriever_name,
                    'metadata': item
                }
                chunks.append(chunk)

    return chunks

def transform_aggregated_results_to_articles(aggregated_output):
    """Transform aggregator output back to article format"""
    articles = []

    try:
        if hasattr(aggregated_output, 'clusters'):
            for cluster in aggregated_output.clusters:
                # Create an article from each cluster
                article = {
                    "id": f"cluster-{hash(str(cluster))}",
                    "date": "Today",
                    "title": getattr(cluster, 'title', 'Cluster Summary'),
                    "source": "Aggregated",
                    "preview": getattr(cluster, 'summary', 'Aggregated news summary'),
                    "sentiment": determine_sentiment(getattr(cluster, 'sentiment', None)),
                    "tags": getattr(cluster, 'tags', []),
                    "url": None,
                    "relevance_score": getattr(cluster, 'relevance_score', 0.7),
                    "category": getattr(cluster, 'category', 'General')
                }
                articles.append(article)

    except Exception as e:
        logger.error(f"Error transforming aggregated results: {e}")
        logger.error(f"Error transforming aggregated results: {e}")

    return articles

# Create database tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
