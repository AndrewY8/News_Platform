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

# Import Google Gemini for AI functionality
import google.generativeai as genai

# Import News Agent System
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from news_agent.agent import PlannerAgent
    from news_agent.aggregator.aggregator import AggregatorAgent
    NEWS_AGENT_AVAILABLE = True
    print("News Agent System available")
except Exception as e:
    NEWS_AGENT_AVAILABLE = False
    print(f"News Agent System not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "1f96d48a73e24ad19d3e68449d982290")
newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

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
        aggregator_agent = AggregatorAgent()
        logger.info("🚀 News Agent System initialized successfully")
    except Exception as e:
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

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List[Dict]] = []

class EnhancedSearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    use_agent: bool = True
    limit: int = 10

# Configure Gemini
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
cors_origins = ["http://localhost:3000", "http://localhost:3001"]
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
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import all handler modules
from query_handler.chat_router import add_chat_routes
from query_handler.article_retriever_router import add_article_retrieval_routes
from query_handler.chat_history_routes import add_chat_history_routes
from ticker_handler.ticker_routes import add_ticker_routes
from db_handler.user_routes import add_user_routes

# Add all routes from handlers
add_chat_routes(app, limiter, get_db, User, ChatHistory)
add_article_retrieval_routes(app, limiter, get_db, Article)
add_chat_history_routes(app, limiter, get_db, ChatHistory)
add_ticker_routes(app, limiter, get_db, User)
add_user_routes(app, limiter, get_db, User, Article)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "News Platform API", "status": "running", "version": "1.0"}

# Additional saved articles route
@app.get("/api/articles/saved")
@limiter.limit("30/minute")
async def get_saved_articles(request: Request, db: Session = Depends(get_db)):
    """Get saved articles"""
    try:
        # Get saved articles from database
        saved = db.query(Article).filter(Article.saved == True).limit(20).all()

        def format_article_date(date_input):
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
            tags = []
            for field in ['tags', 'keywords', 'topics', 'symbols']:
                if field in item and item[field]:
                    if isinstance(item[field], list):
                        tags.extend([str(tag) for tag in item[field]])
                    else:
                        tags.append(str(item[field]))
            return list(set(tags))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)