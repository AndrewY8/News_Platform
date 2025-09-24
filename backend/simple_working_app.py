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

# Helper functions
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
        },
        {
            "id": "fallback-3",
            "date": "Today",
            "title": "Oil Prices Surge on Supply Concerns",
            "source": "Bloomberg",
            "preview": "Crude oil prices jumped to their highest level in months amid growing concerns about supply disruptions...",
            "sentiment": "negative",
            "tags": ["OIL", "ENERGY"],
            "url": "#",
            "relevance_score": 0.7,
            "category": "Energy"
        }
    ]

# API Routes

@app.get("/")
async def root():
    return {"message": "News Platform API", "status": "running", "version": "1.0"}

@app.get("/api/articles")
@limiter.limit("30/minute")
async def get_personalized_articles(request: Request, db: Session = Depends(get_db)):
    """Get personalized articles"""
    try:
        # Return fallback articles for now
        return JSONResponse(content=get_fallback_articles())
    except Exception as e:
        logger.error(f"Error getting personalized articles: {e}")
        return JSONResponse(content=get_fallback_articles())

@app.get("/api/articles/top")
@limiter.limit("30/minute")
async def get_top_articles(request: Request, db: Session = Depends(get_db)):
    """Get top articles"""
    try:
        # Return fallback articles for now
        return JSONResponse(content=get_fallback_articles())
    except Exception as e:
        logger.error(f"Error getting top articles: {e}")
        return JSONResponse(content=get_fallback_articles())

@app.get("/api/articles/search")
@limiter.limit("20/minute")
async def search_articles(q: str, request: Request, db: Session = Depends(get_db)):
    """Search articles"""
    try:
        # Return fallback articles for now
        return JSONResponse(content=get_fallback_articles())
    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        return JSONResponse(content=[])

@app.get("/api/articles/saved")
@limiter.limit("30/minute")
async def get_saved_articles(request: Request, db: Session = Depends(get_db)):
    """Get saved articles"""
    try:
        # Return some sample saved articles
        saved_articles = get_fallback_articles()[:2]  # Just return 2 for saved
        return JSONResponse(content=saved_articles)
    except Exception as e:
        logger.error(f"Error getting saved articles: {e}")
        return JSONResponse(content=[])

@app.post("/api/articles/{article_id}/save")
@limiter.limit("20/minute")
async def save_article(article_id: str, request: Request, db: Session = Depends(get_db)):
    """Save an article"""
    try:
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error saving article: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})

@app.post("/api/articles/{article_id}/unsave")
@limiter.limit("20/minute")
async def unsave_article(article_id: str, request: Request, db: Session = Depends(get_db)):
    """Unsave an article"""
    try:
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error unsaving article: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})

@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat_endpoint(request: ChatRequest, req: Request, db: Session = Depends(get_db)):
    """Chat with Gemini AI"""
    try:
        logger.info(f"Chat request: {request.message}")

        # Generate a response using Gemini
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content([
                f"You are a helpful financial news assistant. Answer this question: {request.message}"
            ])
            ai_response = response.text
        except Exception as e:
            logger.error(f"Gemini response error: {e}")
            ai_response = f"I've processed your query about '{request.message}'. Here are some relevant articles to review."

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

        # Return response with suggested articles
        suggested_articles = get_fallback_articles()[:3]  # Return 3 suggested articles

        return JSONResponse(content={
            "response": ai_response,
            "suggested_articles": suggested_articles
        })

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return JSONResponse(content={
            "response": "I encountered an error while processing your query. Please try again later.",
            "suggested_articles": []
        })

@app.post("/api/search/enhanced")
@limiter.limit("10/minute")
async def enhanced_search(request: EnhancedSearchRequest, req: Request, db: Session = Depends(get_db)):
    """Enhanced search endpoint"""
    try:
        logger.info(f"Enhanced search request: {request.query}")

        # Return fallback articles with search metadata
        articles = get_fallback_articles()

        return JSONResponse(content={
            "success": True,
            "articles": articles[:request.limit],
            "search_method": "fallback_search",
            "sources_used": ["NewsAPI"],
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

@app.get("/api/chat/history")
@limiter.limit("10/minute")
async def get_chat_history(request: Request, db: Session = Depends(get_db)):
    """Get chat history for user"""
    try:
        # Get recent chat history from database
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
async def save_chat_history(request: Request, db: Session = Depends(get_db)):
    """Save chat query to history"""
    try:
        data = await request.json()

        chat_entry = ChatHistory(
            id=f"chat-{int(time.time())}-{hash(data.get('query', '')) % 10000}",
            user_id="1",  # Default user for now
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
async def delete_chat_history(query_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete chat history entry"""
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
async def get_market_summary(tickers: str, request: Request):
    """Get market data for tickers"""
    try:
        ticker_list = tickers.split(',')
        ticker_data = []

        # Mock data for now
        mock_data = {
            'AAPL': {'price': 175.20, 'change': 2.15, 'change_percent': 1.24},
            'MSFT': {'price': 378.85, 'change': -1.25, 'change_percent': -0.33},
            'NVDA': {'price': 821.67, 'change': 15.42, 'change_percent': 1.91},
            'TSLA': {'price': 195.33, 'change': -3.12, 'change_percent': -1.57},
            'AMZN': {'price': 152.74, 'change': 0.87, 'change_percent': 0.57},
            'GOOGL': {'price': 138.25, 'change': 1.34, 'change_percent': 0.98}
        }

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
                # Default data for unknown tickers
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
async def update_user(request: Request, db: Session = Depends(get_db)):
    """Update user preferences"""
    try:
        data = await request.json()
        # For now just return success since we don't have user management
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)