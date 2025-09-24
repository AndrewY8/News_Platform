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
<<<<<<< HEAD
from fastapi import Query
# from textblob import TextBlob  # Temporarily disabled due to NumPy version conflict
=======
>>>>>>> 8307a4c (changed backend)

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
import google.generativeai as genai

# Import News Agent System
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

# Configure Gemini
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
cors_origins = ["http://localhost:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Required for cookies/sessions
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Accept-Language", "Content-Language"],
)


<<<<<<< HEAD
# Utility functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# OAuth Authentication Endpoints


@app.get("/auth/login/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow"""
    if provider not in ["google", "github"]:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")

    # Check if in demo mode (OAuth credentials not configured)
    if provider == "google" and (
        not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == "demo-mode-google-client-id"
    ):
        return {
            "demo_mode": True,
            "provider": provider,
            "message": "Demo mode - OAuth not configured",
        }

    if provider == "github" and (
        not GITHUB_CLIENT_ID or GITHUB_CLIENT_ID == "demo-mode-github-client-id"
    ):
        return {
            "demo_mode": True,
            "provider": provider,
            "message": "Demo mode - OAuth not configured",
        }

    # Generate secure state parameter
    state = auth_system.generate_secure_state()

    # Store state in session (in production, use Redis or secure session storage)
    request.session["oauth_state"] = state
    request.session["oauth_provider"] = provider

    # Get OAuth client
    client = auth_system.oauth.create_client(provider)
    redirect_uri = f"{BACKEND_URL}/auth/callback/{provider}"

    return await client.authorize_redirect(request, redirect_uri, state=state)


@app.get("/auth/callback/{provider}")
async def oauth_callback(
    provider: str, request: Request, db: Session = Depends(get_db)
):
    """Handle OAuth callback"""
    if provider not in ["google", "github"]:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")

    # Verify state parameter
    state = request.query_params.get("state")
    stored_state = request.session.get("oauth_state")
    stored_provider = request.session.get("oauth_provider")

    if (
        not state
        or not stored_state
        or state != stored_state
        or provider != stored_provider
    ):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Clear session state
    request.session.pop("oauth_state", None)
    request.session.pop("oauth_provider", None)

    try:
        # Get OAuth client and exchange code for token
        client = auth_system.oauth.create_client(provider)
        token = await client.authorize_access_token(request)

        # Get user information from provider
        if provider == "google":
            user_info = await auth_system.get_google_user_info(token["access_token"])
        elif provider == "github":
            user_info = await auth_system.get_github_user_info(token["access_token"])
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        if not user_info:
            raise HTTPException(
                status_code=400, detail="Failed to get user information"
            )

        # Create or update user in database
        user = await create_or_update_user(user_info, db)

        # Generate JWT tokens
        auth_tokens = auth_system.create_auth_tokens(user_info)

        # Redirect to frontend with tokens
        frontend_url = f"{FRONTEND_URL}/auth/success?access_token={auth_tokens.access_token}&refresh_token={auth_tokens.refresh_token}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        error_url = f"{FRONTEND_URL}/auth/error?message=Authentication failed"
        return RedirectResponse(url=error_url)


@app.post("/auth/demo-login")
async def demo_login(request: DemoLoginRequest, db: Session = Depends(get_db)):
    """Demo login for development (when OAuth not configured)"""
    if request.provider not in ["google", "github"]:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    # Create demo user
    demo_user_info = UserInfo(
        id=f"demo_{request.provider}_{request.email.replace('@', '_').replace('.', '_')}",
        email=request.email,
        name=f"Demo User ({request.provider.title()})",
        picture=None,
        provider=request.provider,
        verified=True,
    )

    # Create or update user in database
    user = await create_or_update_user(demo_user_info, db)

    # Generate JWT tokens
    auth_tokens = auth_system.create_auth_tokens(demo_user_info)

    return auth_tokens


@app.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    token_data = auth_system.verify_token(refresh_token, "refresh")
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Create new access token
    new_access_token = auth_system.create_access_token(
        {
            "sub": token_data.user_id,
            "email": token_data.email,
            "provider": token_data.provider,
        }
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


@app.post("/auth/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """Logout user (in production, add token to blacklist)"""
    # In production, add the token to a blacklist in Redis
    # For now, just return success (client should discard tokens)
    return {"message": "Successfully logged out"}


@app.get("/auth/me")
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current authenticated user information"""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "provider": user.provider,
        "avatar_url": user.avatar_url,
        "verified": user.verified,
        "trades": json.loads(user.trades) if user.trades else [],
        "preferences": json.loads(user.preferences) if user.preferences else {},
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


# Helper function for user management
async def create_or_update_user(user_info: UserInfo, db: Session) -> User:
    """Create or update user in database"""
    user = db.query(User).filter(User.id == user_info.id).first()

    if user:
        # Update existing user
        user.email = user_info.email
        user.full_name = user_info.name
        user.avatar_url = user_info.picture
        user.verified = user_info.verified
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()
    else:
        # Create new user
        user = User(
            id=user_info.id,
            email=user_info.email,
            username=user_info.email.split("@")[0],  # Use email prefix as username
            full_name=user_info.name,
            provider=user_info.provider,
            provider_id=user_info.id,
            avatar_url=user_info.picture,
            verified=user_info.verified,
            trades=json.dumps([]),
            preferences=json.dumps({}),
            last_login=datetime.utcnow(),
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user


# News fetching function
def fetch_news_from_newsapi(user_preferences: dict) -> List[dict]:
    """Fetch news from NewsAPI based on user preferences"""
    articles = []

    try:
        # Get user's tickers
        tickers = user_preferences.get("explicit_preferences", {}).get("tickers", [])

        if tickers:
            # Fetch news for each ticker
            for ticker in tickers[:3]:  # Limit to 3 tickers to avoid rate limits
                try:
                    # Search for company news
                    response = newsapi.get_everything(
                        q=ticker, language="en", sort_by="publishedAt", page_size=10
                    )

                    for article in response["articles"]:
                        articles.append(
                            {
                                "title": article["title"],
                                "description": article["description"] or "",
                                "url": article["url"],
                                "publishedAt": article["publishedAt"],
                                "source": (
                                    article["source"]["name"]
                                    if article["source"]
                                    else "Unknown"
                                ),
                                "content": article["content"] or "",
                            }
                        )

                except Exception as e:
                    logger.error(f"Error fetching news for ticker {ticker}: {e}")
                    continue

        # If no tickers or no articles found, get general business news
        if not articles:
            try:
                response = newsapi.get_top_headlines(
                    category="business", language="en", country="us", page_size=20
                )

                for article in response["articles"]:
                    articles.append(
                        {
                            "title": article["title"],
                            "description": article["description"] or "",
                            "url": article["url"],
                            "publishedAt": article["publishedAt"],
                            "source": (
                                article["source"]["name"]
                                if article["source"]
                                else "Unknown"
                            ),
                            "content": article["content"] or "",
                        }
                    )

            except Exception as e:
                logger.error(f"Error fetching general news: {e}")

    except Exception as e:
        logger.error(f"Error in fetch_news_from_newsapi: {e}")

    return articles


# API Endpoints
@app.get("/api/articles", response_model=List[ArticleModel])
@limiter.limit("100/minute")
async def get_articles(
    request: Request,
    tickers: str = Query(None),  # <- this tells FastAPI to read ?tickers=...
    db=Depends(get_db)
):
    """Get personalized articles using NEW Gemini-powered system"""
    
    if tickers:
        user_tickers = tickers.split(",")
    else:
        # fallback to saved trades
        user = db.query(User).first()
        user_tickers = eval(user.trades) if user and user.trades else []

    # Get or create user (simplified for demo)
    user = db.query(User).first()
    if not user:
        user = User(
            id="1",
            username="demo_user",
            email="demo@example.com",
            provider="demo",
            provider_id="demo_1",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get user preferences
    # user_tickers = eval(user.trades) if user.trades else []
    user_preferences = {
        "investment_style": "balanced",
        "experience_level": "intermediate",
    }

    logger.info(f"🔍 Getting articles for user with tickers: {user_tickers}")

    if not user_tickers:
        logger.warning(
            "⚠️ No tickers found for user! They need to add tickers in the Tickers tab."
        )

    try:
        # Use the consolidated News Intelligence service
        planner = create_enhanced_planner(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            max_retrievers=5,
            config_overrides={
                'clustering': {
                    'min_cluster_size': 2,
                    'similarity_threshold': 0.65
                },
                'summarization': {
                    'max_tokens': 200,
                    'temperature': 0.3
                }
            }
        )
        
        processed_articles = []
        print("tickers:", user_tickers)
        for query in user_tickers:
            results = await planner.run_async(
                query=query,
                user_preferences=user_preferences,
                return_aggregated=True
            )
            # results is a list of retriever dicts, extend instead of append
            processed_articles.append((results, query))
            print(f"Processed articles for query '{query}': {results}")

        # Convert to response model
             
        response_articles = []
        # print(retriever.get("retreiver") for retriever in processed_articles)

        for retriever_list, ticker in processed_articles:
            for retriever_data in retriever_list:
                if retriever_data.get("retriever") == "EDGARRetriever":
                    for article in retriever_data.get("results", []):
                        article_datetime = datetime.strptime(article.get("filing_date"), "%Y-%m-%d")
                        timestamp = int(article_datetime.timestamp())
                        response_articles.append(
                            ArticleModel(
                                id=article.get("accession_number"),
                                headline=article.get("title"),
                                summary=article.get("body"),
                                url=article.get("href"),
                                datetime=timestamp,
                                category=article.get("form_type"),
                                sentiment_score=None,
                                relevance_score=None,
                                source="EDGAR",
                                tags=ticker,
                            )
                        )
                if retriever_data.get("retriever") == "ExaRetriever":
                    for article in retriever_data.get("results", []):
                        # Handle published_date
                        published_date = getattr(article, "published_date", None)
                        if published_date:
                            article_datetime = datetime.strptime(published_date[:10], "%Y-%m-%d")
                            timestamp = int(article_datetime.timestamp())
                        else:
                            timestamp = int(datetime.utcnow().timestamp())

                        # Use URL as ID
                        article_id = getattr(article, "url", "no-id")

                        # Headline fallback to URL if no title
                        headline = getattr(article, "title", None) or "No title"
                        summary = getattr(article, "summary", None) or "No summary"

                        response_articles.append(
                            ArticleModel(
                                id=article_id,
                                headline=headline,
                                summary=summary,
                                url=article_id,
                                datetime=timestamp,
                                category="News",
                                sentiment_score=None,
                                relevance_score=None,
                                source="ExaRetriever",
                                tags=ticker,
                            )
                        )
                        
        response_articles = sorted(response_articles, key=lambda x: x.datetime, reverse=True)[:20]

        return response_articles

    except Exception as e:
        logger.error(f"❌ Error in get_articles: {e}")
        logger.info("🔄 Exception fallback: trying to return existing articles...")

        try:
            # Fallback: return existing articles even if there's an exception
            existing_relevant_articles = (
                db.query(Article)
                .filter(
                    Article.relevance_score.isnot(None), Article.relevance_score > 0.4
                )
                .order_by(Article.datetime.desc())
                .limit(20)
                .all()
            )

            if existing_relevant_articles:
                response_articles = []
                for article in existing_relevant_articles:
                    response_articles.append(
                        ArticleModel(
                            id=article.id,
                            headline=article.headline,
                            summary=article.summary,
                            url=article.url,
                            datetime=article.datetime,
                            category=article.category,
                            sentiment_score=article.sentiment_score,
                            relevance_score=article.relevance_score,
                            source=article.source,
                            tags=(
                                article.tags
                                if hasattr(article, "tags")
                                else article.content_analysis
                            ),
                        )
                    )

                logger.info(
                    f"✅ Exception fallback: returning {len(response_articles)} existing articles"
                )
                return response_articles
            else:
                logger.warning("📭 Exception fallback: no existing articles found")
                return []
        except Exception as fallback_error:
            logger.error(f"❌ Fallback also failed: {fallback_error}")
            return []


@app.get("/api/articles/top", response_model=List[ArticleModel])
@limiter.limit("100/minute")
async def get_top_articles(request: Request, db=Depends(get_db)):
    """Get personalized articles for top news section"""
    try:
        # For now, return the same personalized feed for top news
        # Get or create user (simplified for demo)
        user = db.query(User).first()
        if not user:
            user = User(
                id="demo_1",
                username="demo_user",
                email="demo@example.com",
                provider="demo",
                provider_id="demo_1",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create simple user profile for news fetching
        user_tickers = eval(user.trades) if user.trades else []
        user_profile = {
            "investment_style": "balanced",
            "experience_level": "intermediate",
            "tickers": user_tickers,
        }
        fresh_news = []  # TODO: Implement top news fetching

        # Process and store new articles
        for news_item in fresh_news:
            # Create unique ID
            article_id = hashlib.md5(
                f"{news_item['title']}{news_item['publishedAt']}".encode()
            ).hexdigest()

            # Check if article already exists
            existing_article = (
                db.query(Article).filter(Article.id == article_id).first()
            )
            if existing_article:
                continue

            # Analyze article content
            analysis_result = (
                personalization_orchestrator.content_analyzer.analyze_article(news_item)
            )

            # Create new article
            new_article = Article(
                id=article_id,
                headline=news_item["title"],
                summary=news_item.get("description", ""),
                url=news_item["url"],
                datetime=int(
                    datetime.fromisoformat(
                        news_item["publishedAt"].replace("Z", "+00:00")
                    ).timestamp()
                ),
                content_analysis=str(analysis_result),
                sentiment_score=analysis_result.get("sentiment", {}).get("score", 0.0),
                category=(
                    analysis_result.get("topics", ["General"])[0]
                    if analysis_result.get("topics")
                    else "General"
                ),
                source=news_item.get("source", {}).get("name", "Unknown"),
                tags=analysis_result.get("topics", []),
                relevance_score=0.8,
            )
            db.add(new_article)

        db.commit()

        # Get personalized articles using the correct method signature
        user_tickers = eval(user.trades) if user.trades else []
        user_preferences = {
            "investment_style": "balanced",
            "experience_level": "intermediate",
        }
        personalized_articles = await news_intelligence.get_personalized_news(
            user_tickers, user_preferences, limit=20
        )

        # Convert to response model (articles from news_intelligence are dicts)
        response_articles = []
        for article in personalized_articles:
            # Generate article ID from URL hash
            article_id = hashlib.md5(article.get("url", "").encode()).hexdigest()

            response_articles.append(
                ArticleModel(
                    id=article_id,
                    headline=article.get("title", ""),
                    summary=article.get("description", ""),
                    url=article.get("url", ""),
                    datetime=(
                        int(
                            time.mktime(
                                datetime.strptime(
                                    article.get("publishedAt", "")[:19],
                                    "%Y-%m-%dT%H:%M:%S",
                                ).timetuple()
                            )
                        )
                        if article.get("publishedAt")
                        else int(time.time())
                    ),
                    category=article.get("category", "general"),
                    sentiment_score=article.get("sentiment_score", 0.0),
                    relevance_score=article.get("relevance_score", 0.5),
                    source=article.get("source", {}).get("name", "Unknown"),
                    tags=None,
                )
            )

        return response_articles

    except Exception as e:
        logger.error(f"Error fetching top articles: {e}")
        return []


@app.post("/api/articles/{article_id}/save")
def save_article(article_id: str, db=Depends(get_db)):
    db = SessionLocal()
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.saved = True
    article.removed = False
    db.commit()
    db.close()
    return {"status": "saved"}


@app.post("/api/articles/{article_id}/remove")
def remove_article(article_id: str, db=Depends(get_db)):
    db = SessionLocal()
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.removed = True
    article.saved = False
    db.commit()
    db.close()
    return {"status": "removed"}


@app.post("/api/interactions")
def record_interaction(interaction: InteractionModel, db=Depends(get_db)):
    """Record user interaction for learning"""

    # Get or create user (simplified for demo)
    user = db.query(User).first()
    if not user:
        user = User(
            id="demo_1",
            username="demo_user",
            email="demo@example.com",
            provider="demo",
            provider_id="demo_1",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create interaction record
    new_interaction = UserInteraction(
        user_id=user.id,
        article_id=interaction.article_id,
        interaction_type=interaction.interaction_type,
        duration=interaction.duration,
        timestamp=datetime.utcnow(),
    )

    db.add(new_interaction)
    db.commit()

    # Update user profile (learning) - TODO: Implement learning system
    # news_intelligence.learning_engine.update_user_profile(
    #     user.id, new_interaction, db
    # )

    return {"status": "recorded"}


@app.get("/api/saved", response_model=List[ArticleModel])
def get_saved(db=Depends(get_db)):
    articles = db.query(Article).filter(Article.saved == True).all()
    return [
        ArticleModel(
            id=article.id,
            headline=article.headline,
            summary=article.summary,
            url=article.url,
            datetime=article.datetime,
            category=article.category,
            sentiment_score=article.sentiment_score,
            relevance_score=article.relevance_score,
            source=article.source,
            tags=article.tags,
        )
        for article in articles
    ]


@app.get("/api/user", response_model=UserModel)
def get_user(db=Depends(get_db)):
    user = db.query(User).first()
    if not user:
        user = User(
            id="demo_1",
            username="demo_user",
            email="demo@example.com",
            provider="demo",
            provider_id="demo_1",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {
        "username": user.username,
        "email": user.email,
        "trades": eval(user.trades) if user.trades else [],
    }


@app.post("/api/user", response_model=UserModel)
def update_user(user_data: UserModel, db=Depends(get_db)):
    # Validate tickers before saving
    validation_result = validate_ticker_list(user_data.trades)

    # Log validation results
    if validation_result["invalid_tickers"]:
        logger.warning(
            f"Invalid tickers rejected: {validation_result['invalid_tickers']}"
        )
    if validation_result["warnings"]:
        logger.info(f"Ticker warnings: {validation_result['warnings']}")

    user = db.query(User).first()
    if not user:
        user = User(username=user_data.username, email=user_data.email)
        db.add(user)

    # Only save valid tickers
    user.trades = str(validation_result["valid_tickers"])
    db.commit()
    db.refresh(user)

    response_data = {
        "username": user.username,
        "email": user.email,
        "trades": eval(user.trades) if user.trades else [],
    }

    # Add validation feedback to response
    if validation_result["invalid_tickers"] or validation_result["warnings"]:
        response_data["validation"] = {
            "rejected_tickers": validation_result["invalid_tickers"],
            "warnings": validation_result["warnings"],
        }

    return response_data


@app.get("/api/ticker-suggestions")
def get_ticker_suggestions_endpoint(q: str = ""):
    """Get ticker suggestions for autocomplete"""
    suggestions = get_ticker_suggestions(q, limit=10)
    return {"suggestions": suggestions}


# Enhanced Pipeline Helper Functions
def _should_use_enhanced_pipeline(message: str) -> bool:
    """Always use enhanced pipeline when available (user preference)."""
    return True  # Always use enhanced pipeline when available

def _extract_topics_from_message(message: str) -> List[str]:
    """Extract topics from user message."""
    topics = []
    message_lower = message.lower()

    topic_mapping = {
        'technology': ['tech', 'ai', 'artificial intelligence', 'software', 'hardware'],
        'automotive': ['car', 'vehicle', 'auto', 'electric vehicle', 'ev'],
        'healthcare': ['health', 'medical', 'pharma', 'drug', 'treatment'],
        'finance': ['bank', 'finance', 'loan', 'credit', 'payment'],
        'energy': ['oil', 'gas', 'renewable', 'solar', 'wind', 'battery'],
        'retail': ['store', 'shopping', 'consumer', 'retail', 'e-commerce']
    }

    for topic, keywords in topic_mapping.items():
        if any(keyword in message_lower for keyword in keywords):
            topics.append(topic)

    return topics

def _extract_keywords_from_message(message: str) -> List[str]:
    """Extract keywords from user message."""
    financial_keywords = [
        'earnings', 'revenue', 'profit', 'loss', 'growth', 'decline',
        'merger', 'acquisition', 'ipo', 'sec filing', 'quarterly',
        'annual', 'guidance', 'outlook', 'forecast'
    ]

    message_lower = message.lower()
    keywords = [kw for kw in financial_keywords if kw in message_lower]
    return keywords

async def _generate_ai_response_from_pipeline(message: str, pipeline_results: Dict[str, Any], user_tickers: List[str]) -> str:
    """Generate AI response based on pipeline results."""
    try:
        # Create context from pipeline results
        key_points = pipeline_results.get('key_points', [])
        final_articles = pipeline_results.get('final_articles', [])

        # Build context string
        context_parts = []

        if key_points:
            context_parts.append("Key insights discovered:")
            for kp in key_points[:3]:
                context_parts.append(f"- {kp.get('original_title', kp.get('query', 'Key insight'))}")

        if final_articles:
            context_parts.append(f"\nFound {len(final_articles)} relevant articles from reputable sources")

        context = "\n".join(context_parts)

        # Use existing news intelligence for response generation
        response = await news_intelligence.generate_chat_response_with_context(
            message, context, user_tickers
        )

        return response if isinstance(response, str) else response.get('response', '')

    except Exception as e:
        logger.error(f"AI response generation failed: {e}")
        return f"Based on my analysis of recent news, I found several relevant insights about your query: {message}"

def _format_enhanced_pipeline_response(ai_response: str, pipeline_results: Dict[str, Any], original_message: str) -> Dict[str, Any]:
    """Format the pipeline response for frontend consumption."""
    final_articles = pipeline_results.get('final_articles', [])
    processing_stats = pipeline_results.get('processing_stats', {})
    stages = pipeline_results.get('stages', {})

    # Convert articles to frontend format
    suggested_articles = []
    for article in final_articles:
        suggested_article = {
            'id': article.get('id', ''),
            'title': article.get('title', ''),
            'source': article.get('source', ''),
            'preview': article.get('preview', ''),
            'url': article.get('url', ''),
            'sentiment': article.get('sentiment', 'neutral'),
            'tags': article.get('tags', []),
            'relevance_score': article.get('relevance_score', 0.5),
            'category': article.get('category', 'news'),
            'date': article.get('timestamp', datetime.now().isoformat())
        }
        suggested_articles.append(suggested_article)

    return {
        "response": ai_response,
        "suggested_articles": suggested_articles,
        "success": True,
        "search_method": "enhanced_pipeline",
        "enhanced_pipeline_used": True,
        "pipeline_metadata": {
            "total_duration": processing_stats.get('total_duration', 0),
            "stages_completed": len(stages),
            "final_article_count": len(final_articles),
            "key_points_extracted": len(pipeline_results.get('key_points', [])),
            "original_query": original_message
        },
        "sources_used": list(set([article.get('source', 'Unknown') for article in final_articles])),
        "processing_time": processing_stats.get('total_duration', 0)
    }

# NEW: Chat functionality with Gemini
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List[dict]] = None


class ChatHistoryModel(BaseModel):
    id: str
    query: str
    response: Optional[str] = None
    timestamp: datetime


@app.post("/api/chat")
async def chat_about_news(request: ChatRequest, db: Session = Depends(get_db)):
    """Enhanced chat with multi-stage news discovery pipeline and fallback support"""

    try:
        # Get user context
        user = db.query(User).filter(User.id == str(request.user_id)).first()
        if not user:
            user = db.query(User).first()  # Fall back to first user
            if not user:
                return {"error": "No user found", "success": False}

        user_tickers = eval(user.trades) if user.trades else []

        logger.info(
            f"💬 Enhanced Chat request: '{request.message}' from user with tickers: {user_tickers}"
        )

        # Step 1: Try Enhanced Pipeline (if available)
        if enhanced_pipeline and _should_use_enhanced_pipeline(request.message):
            try:
                logger.info("🚀 Using Enhanced Multi-Stage Pipeline")

                # Prepare user preferences
                user_preferences = {
                    'watchlist': user_tickers,
                    'topics': _extract_topics_from_message(request.message),
                    'keywords': _extract_keywords_from_message(request.message)
                }

                # Run the enhanced pipeline
                pipeline_results = await enhanced_pipeline.discover_news(
                    request.message, user_preferences
                )

                if pipeline_results['processing_stats']['success']:
                    # Generate AI response based on pipeline results
                    ai_response = await _generate_ai_response_from_pipeline(
                        request.message, pipeline_results, user_tickers
                    )

                    # Format for frontend
                    enhanced_response = _format_enhanced_pipeline_response(
                        ai_response, pipeline_results, request.message
                    )

                    logger.info(f"✅ Enhanced pipeline response completed")
                    logger.info(f"📊 Pipeline stats: {pipeline_results['processing_stats']}")

                    return enhanced_response
                else:
                    logger.warning("Enhanced pipeline execution failed, falling back")

            except Exception as e:
                logger.error(f"Enhanced pipeline failed: {e}")
                # Continue to fallbacks

        # Step 2: Fallback to Simple Agent
        logger.info("📰 Using Simple Agent Service (fallback)")
        agent_service = get_simple_agent_news_service()

        chat_result = await agent_service.generate_enhanced_chat_response(
            request.message,
            user_tickers,
            use_agent_search=True
        )

        if chat_result.get("success"):
            logger.info(f"✅ Simple agent response generated successfully")
            logger.info(f"🔍 Search method: {chat_result.get('search_method', 'unknown')}")

            # Add enhanced pipeline metadata
            chat_result['enhanced_pipeline_available'] = enhanced_pipeline is not None
            chat_result['used_enhanced_pipeline'] = False

            if chat_result.get('sources_used'):
                logger.info(f"📊 Agent sources used: {chat_result['sources_used']}")

            return chat_result
        else:
            # Step 3: Ultimate fallback to traditional method
            logger.warning(f"Simple agent failed, using traditional fallback: {chat_result.get('error')}")

            fallback_result = await news_intelligence.generate_chat_response(
                request.message, user_tickers, request.conversation_history or []
            )

            # Mark as traditional fallback
            if isinstance(fallback_result, dict):
                fallback_result['search_method'] = 'traditional_fallback'
                fallback_result['enhanced_pipeline_available'] = enhanced_pipeline is not None
                fallback_result['used_enhanced_pipeline'] = False

            return fallback_result

    except Exception as e:
        logger.error(f"❌ Enhanced chat error: {e}")
        
        # Try fallback to traditional method
        try:
            logger.info("Attempting fallback to traditional chat method")
            fallback_result = await news_intelligence.generate_chat_response(
                request.message, user_tickers, request.conversation_history or []
            )
            fallback_result['search_method'] = 'error_fallback'
            fallback_result['original_error'] = str(e)
            return fallback_result
        except Exception as fallback_error:
            logger.error(f"❌ Fallback also failed: {fallback_error}")
            return {
                "response": "I'm sorry, I'm having trouble processing your question right now. Please try again.",
                "error": str(e),
                "fallback_error": str(fallback_error),
                "success": False,
            }


@app.post("/api/search/enhanced")
async def enhanced_search_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """Enhanced search endpoint using agent system for personalized news page"""
    
    try:
        query = request.get('query', '')
        user_id = request.get('user_id')
        use_agent = request.get('use_agent', True)
        limit = request.get('limit', 10)
        
        if not query:
            return {"error": "Query is required", "success": False}
        
        # Get user context
        user = db.query(User).filter(User.id == str(user_id)).first() if user_id else None
        if not user:
            user = db.query(User).first()  # Fall back to first user
            
        user_tickers = eval(user.trades) if user and user.trades else []
        
        logger.info(f"🔍 Enhanced search request: '{query}' with tickers: {user_tickers}")
        
        # Get simple agent news service
        agent_service = get_simple_agent_news_service()
        
        # Perform enhanced search
        search_results = await agent_service.enhanced_search(
            query=query,
            user_tickers=user_tickers,
            use_enhanced=use_agent,
            limit=limit
        )
        
        if search_results['success']:
            logger.info(f"✅ Enhanced search completed: {len(search_results['articles'])} articles found")
            logger.info(f"🔍 Search method: {search_results['search_method']}")
            
            return {
                "success": True,
                "articles": search_results['articles'],
                "total_found": search_results['total_found'],
                "search_method": search_results['search_method'],
                "sources_used": search_results.get('agent_sources', []),
                "query": query
            }
        else:
            return {
                "success": False,
                "error": search_results.get('error', 'Search failed'),
                "query": query
            }
            
    except Exception as e:
        logger.error(f"❌ Enhanced search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": request.get('query', '')
        }


@app.get("/api/chat/history")
async def get_chat_history(db: Session = Depends(get_db)):
    """Get chat history for the user"""
    try:
        # For now, get the first user's chat history
        # In a real app, this would use authentication
        user = db.query(User).first()
        if not user:
            return []
            
        history = db.query(ChatHistory).filter(
            ChatHistory.user_id == user.id
        ).order_by(ChatHistory.timestamp.desc()).limit(50).all()
        
        return [
            {
                "id": chat.id,
                "query": chat.query,
                "response": chat.response,
                "timestamp": chat.timestamp.isoformat()
            }
            for chat in history
        ]
    except Exception as e:
        logger.error(f"❌ Error fetching chat history: {e}")
        return []


@app.post("/api/chat/history")
async def save_chat_history(
    request: dict,
    db: Session = Depends(get_db)
):
    """Save chat history entry"""
    try:
        # Get the first user for now
        user = db.query(User).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate a unique ID
        chat_id = hashlib.md5(f"{user.id}_{request['query']}_{time.time()}".encode()).hexdigest()
        
        # Create new chat history entry
        chat_history = ChatHistory(
            id=chat_id,
            user_id=user.id,
            query=request["query"],
            response=request.get("response"),
            timestamp=datetime.utcnow()
        )
        
        db.add(chat_history)
        db.commit()
        
        return {"message": "Chat history saved", "id": chat_id}
        
    except Exception as e:
        logger.error(f"❌ Error saving chat history: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/history/{chat_id}")
async def delete_chat_history(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """Delete a chat history entry"""
    try:
        chat = db.query(ChatHistory).filter(ChatHistory.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat history not found")
            
        db.delete(chat)
        db.commit()
        
        return {"message": "Chat history deleted"}
        
    except Exception as e:
        logger.error(f"❌ Error deleting chat history: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/breaking-news")
@limiter.limit("20/minute")
async def get_breaking_news(request: Request, db: Session = Depends(get_db)):
    """Get breaking news relevant to user's interests"""

    try:
        # Get user preferences
        user = db.query(User).first()
        user_tickers = eval(user.trades) if user and user.trades else []

        logger.info(f"⚡ Getting breaking news for: {user_tickers}")

        # Use smart filter to get breaking news
        breaking_articles = (
            []
        )  # Breaking news functionality moved to news_intelligence module

        return {
            "articles": breaking_articles,
            "count": len(breaking_articles),
            "user_tickers": user_tickers,
        }

    except Exception as e:
        logger.error(f"Error getting breaking news: {e}")
        return {"articles": [], "count": 0, "error": str(e)}


=======
>>>>>>> 8307a4c (changed backend)
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

    return articles

# Create database tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
