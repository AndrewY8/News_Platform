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
from fastapi import Query
# from textblob import TextBlob  # Temporarily disabled due to NumPy version conflict

# import spacy  # Temporarily disabled due to package conflicts
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

# Import our secure auth system
from auth import (
    auth_system,
    get_current_user,
    get_current_user_optional,
    TokenData,
    AuthTokens,
    UserInfo,
)
from ticker_validator import validate_ticker_list, get_ticker_suggestions

# Import new Gemini-powered personalization system
from news_intelligence import NewsIntelligenceService
from simple_agent_integration import get_simple_agent_news_service
import google.generativeai as genai

# Import Enhanced Pipeline (before logger is defined)
ENHANCED_PIPELINE_AVAILABLE = False
enhanced_pipeline_import_error = None
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from enhanced_news_pipeline import create_enhanced_news_pipeline
    ENHANCED_PIPELINE_AVAILABLE = True
except Exception as e:
    enhanced_pipeline_import_error = str(e)

# Import SEC service
from sec_service import sec_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log enhanced pipeline import status
if ENHANCED_PIPELINE_AVAILABLE:
    logger.info("✅ Enhanced News Pipeline available")
else:
    logger.warning(f"⚠️ Enhanced News Pipeline not available: {enhanced_pipeline_import_error}")

# Configuration from environment
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "1f96d48a73e24ad19d3e68449d982290")
newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

# OAuth configuration (imported from environment)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# Security configuration is now handled in auth.py

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_news.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Enhanced Pipeline initialization
enhanced_pipeline = None
if ENHANCED_PIPELINE_AVAILABLE:
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")

        if gemini_key and tavily_key:
            enhanced_pipeline = create_enhanced_news_pipeline(
                gemini_api_key=gemini_key,
                tavily_api_key=tavily_key,
                max_retrievers=5
            )
            logger.info("🚀 Enhanced News Discovery Pipeline initialized successfully")
        else:
            logger.warning("⚠️ Missing API keys for enhanced pipeline (GEMINI_API_KEY, TAVILY_API_KEY)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize enhanced pipeline: {e}")
        enhanced_pipeline = None


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

    # Relationships
    interactions = relationship("UserInteraction", back_populates="article")


class UserInteraction(Base):
    __tablename__ = "user_interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        String, ForeignKey("users.id")
    )  # Fixed: String to match User.id type
    article_id = Column(String, ForeignKey("articles.id"))
    interaction_type = Column(String)  # 'save', 'remove', 'click'
    duration = Column(Integer)  # time spent in seconds
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="interactions")
    article = relationship("Article", back_populates="interactions")


class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


Base.metadata.create_all(bind=engine)


# Pydantic models
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


class UserModel(BaseModel):
    username: str
    email: str
    trades: List[str]
    validation: Optional[dict] = None


class InteractionModel(BaseModel):
    article_id: str
    interaction_type: str
    duration: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Market Data Models
class TickerInfo(BaseModel):
    symbol: str
    name: str
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    volume: Optional[int] = None
    market_cap: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    year_high: Optional[float] = None
    year_low: Optional[float] = None


class MarketSummary(BaseModel):
    tickers: List[TickerInfo]
    last_updated: str


# OAuth Models
class DemoLoginRequest(BaseModel):
    provider: str
    email: str


# Personalization Algorithm Components


class ContentAnalysisEngine:
    def __init__(self):
        try:
            # self.nlp = spacy.load("en_core_web_sm")  # Temporarily disabled
            self.nlp = None
        except (OSError, ImportError, TypeError):
            logger.warning("spaCy model not available. Using fallback analysis.")
            self.nlp = None
        # self.sentiment_analyzer = TextBlob  # Temporarily disabled due to NumPy version conflict
        self.sentiment_analyzer = None

    def analyze_article(self, article_data: dict) -> dict:
        """Comprehensive article analysis"""
        text = article_data.get("title", "") + " " + article_data.get("description", "")

        analysis = {
            "entities": self._extract_entities(text),
            "sentiment": self._analyze_sentiment(text),
            "topics": self._extract_topics(text),
            "readability": self._calculate_readability(text),
            "urgency": self._assess_urgency(article_data.get("title", "")),
            "relevance_indicators": self._extract_relevance_indicators(text),
        }
        return analysis

    def _extract_entities(self, text: str) -> dict:
        """Extract named entities from text"""
        if not self.nlp:
            # Fallback entity extraction
            return {
                "companies": self._extract_companies_fallback(text),
                "people": [],
                "locations": [],
                "dates": [],
                "money": [],
            }

        try:
            doc = self.nlp(text)
            entities = {
                "companies": [ent.text for ent in doc.ents if ent.label_ == "ORG"],
                "people": [ent.text for ent in doc.ents if ent.label_ == "PERSON"],
                "locations": [ent.text for ent in doc.ents if ent.label_ == "GEO"],
                "dates": [ent.text for ent in doc.ents if ent.label_ == "DATE"],
                "money": [ent.text for ent in doc.ents if ent.label_ == "MONEY"],
            }
            return entities
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return {
                "companies": self._extract_companies_fallback(text),
                "people": [],
                "locations": [],
                "dates": [],
                "money": [],
            }

    def _extract_companies_fallback(self, text: str) -> List[str]:
        """Fallback company extraction using simple patterns"""
        companies = []
        # Common company patterns
        company_patterns = [
            r"\b[A-Z]{2,}(?:\.[A-Z]{2,})*\b",  # All caps words (like AAPL, MSFT)
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|Co)\b",  # Company names
        ]

        import re

        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            companies.extend(matches)

        return list(set(companies))[:5]  # Limit to 5 companies

    def _analyze_sentiment(self, text: str) -> dict:
        """Analyze text sentiment"""
        if self.sentiment_analyzer is None:
            # Fallback sentiment analysis - simple keyword-based approach
            positive_words = ['good', 'great', 'excellent', 'positive', 'up', 'rise', 'gain', 'profit', 'success', 'growth']
            negative_words = ['bad', 'poor', 'negative', 'down', 'fall', 'loss', 'decline', 'drop', 'crash', 'failure']
            
            text_lower = text.lower()
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            # Simple polarity calculation
            total = pos_count + neg_count
            polarity = (pos_count - neg_count) / max(total, 1) if total > 0 else 0
            polarity = max(-1, min(1, polarity))  # Clamp to -1, 1
            
            return {
                "polarity": polarity,
                "subjectivity": 0.5,  # Default subjectivity
                "emotion": self._classify_emotion(text),
            }
        
        blob = self.sentiment_analyzer(text)
        return {
            "polarity": blob.sentiment.polarity,  # -1 to 1
            "subjectivity": blob.sentiment.subjectivity,  # 0 to 1
            "emotion": self._classify_emotion(text),
        }

    def _classify_emotion(self, text: str) -> str:
        """Simple emotion classification"""
        text_lower = text.lower()
        if any(
            word in text_lower for word in ["positive", "growth", "profit", "success"]
        ):
            return "positive"
        elif any(
            word in text_lower for word in ["negative", "loss", "decline", "failure"]
        ):
            return "negative"
        else:
            return "neutral"

    def _extract_topics(self, text: str) -> dict:
        """Extract main topics from text"""
        text_lower = text.lower()

        # Simple topic extraction based on keywords
        topics = {
            "earnings": [
                "earnings",
                "quarterly",
                "revenue",
                "profit",
                "financial results",
            ],
            "technology": [
                "tech",
                "software",
                "ai",
                "artificial intelligence",
                "digital",
            ],
            "finance": ["finance", "banking", "investment", "market", "trading"],
            "regulatory": ["regulation", "compliance", "legal", "government", "policy"],
        }

        detected_topics = []
        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_topics.append(topic)

        return {
            "primary_topic": detected_topics[0] if detected_topics else "general",
            "secondary_topics": detected_topics[1:] if len(detected_topics) > 1 else [],
            "keywords": self._extract_keywords(text),
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords"""
        # Simple keyword extraction
        words = text.lower().split()
        # Filter out common words and short words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return keywords[:10]  # Return top 10 keywords

    def _calculate_readability(self, text: str) -> dict:
        """Calculate readability metrics"""
        words = text.split()
        sentences = text.split(".")

        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_sentence_length": len(words) / len(sentences) if sentences else 0,
            "complexity_level": "intermediate" if len(words) > 100 else "simple",
        }

    def _assess_urgency(self, headline: str) -> float:
        """Assess how urgent/time-sensitive the article is"""
        urgency_indicators = [
            "breaking",
            "urgent",
            "immediate",
            "just in",
            "live",
            "developing",
            "update",
            "alert",
        ]

        urgency_score = 0
        headline_lower = headline.lower()
        for indicator in urgency_indicators:
            if indicator in headline_lower:
                urgency_score += 0.2

        return min(urgency_score, 1.0)

    def _extract_relevance_indicators(self, text: str) -> dict:
        """Extract indicators of article relevance"""
        return {
            "market_impact": self._assess_market_impact(text),
            "sector_relevance": self._assess_sector_relevance(text),
            "geographic_relevance": self._assess_geographic_relevance(text),
        }

    def _assess_market_impact(self, text: str) -> float:
        """Assess potential market impact"""
        impact_indicators = [
            "stock",
            "market",
            "trading",
            "price",
            "shares",
            "investor",
        ]
        text_lower = text.lower()
        impact_score = sum(
            0.15 for indicator in impact_indicators if indicator in text_lower
        )
        return min(impact_score, 1.0)

    def _assess_sector_relevance(self, text: str) -> float:
        """Assess sector relevance"""
        sectors = ["technology", "finance", "healthcare", "energy", "consumer"]
        text_lower = text.lower()
        sector_score = sum(0.2 for sector in sectors if sector in text_lower)
        return min(sector_score, 1.0)

    def _assess_geographic_relevance(self, text: str) -> float:
        """Assess geographic relevance"""
        regions = ["us", "usa", "united states", "europe", "asia", "china", "japan"]
        text_lower = text.lower()
        geo_score = sum(0.15 for region in regions if region in text_lower)
        return min(geo_score, 1.0)


class UserProfileEngine:
    def __init__(self):
        self.profile_weights = {
            "explicit_preferences": 0.3,
            "implicit_preferences": 0.4,
            "temporal_factors": 0.2,
            "social_signals": 0.1,
        }

    def build_user_profile(self, user_id: int, db) -> dict:
        """Build comprehensive user profile"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return self._get_default_profile()

        interactions = (
            db.query(UserInteraction).filter(UserInteraction.user_id == user_id).all()
        )

        profile = {
            "explicit_preferences": self._extract_explicit_preferences(user),
            "implicit_preferences": self._learn_implicit_preferences(interactions),
            "temporal_patterns": self._analyze_temporal_patterns(interactions),
            "engagement_metrics": self._calculate_engagement_metrics(interactions),
            "content_affinities": self._analyze_content_affinities(interactions),
        }
        return profile

    def _get_default_profile(self) -> dict:
        """Return default profile for new users"""
        return {
            "explicit_preferences": {"tickers": [], "categories": [], "sources": []},
            "implicit_preferences": {
                "categories": {},
                "sentiment_preference": 0,
                "article_length_preference": "medium",
            },
            "temporal_patterns": {"peak_usage_hours": [9, 12, 17], "recency_bias": 0.7},
            "engagement_metrics": {
                "avg_time_spent": 30,
                "click_through_rate": 0.1,
                "save_rate": 0.05,
            },
            "content_affinities": {
                "topic_affinities": {},
                "entity_affinities": {"companies": [], "people": []},
            },
        }

    def _extract_explicit_preferences(self, user: User) -> dict:
        """Extract user's explicitly stated preferences"""
        trades = eval(user.trades) if user.trades else []
        return {
            "tickers": trades,
            "categories": ["business", "technology", "finance"],  # Default categories
            "sources": ["reuters", "bloomberg", "cnbc"],
            "excluded_sources": [],
        }

    def _learn_implicit_preferences(self, interactions: List[UserInteraction]) -> dict:
        """Learn preferences from user behavior patterns"""
        preferences = {
            "categories": {},
            "sources": {},
            "sentiment_preference": 0,
            "article_length_preference": "medium",
            "engagement_thresholds": {},
        }

        if not interactions:
            return preferences

        # Analyze interaction patterns
        for interaction in interactions:
            if interaction.article:
                # Update category preferences based on engagement
                if interaction.article.category:
                    if interaction.article.category not in preferences["categories"]:
                        preferences["categories"][interaction.article.category] = 0

                    # Weight based on interaction type
                    weight = 0.1
                    if interaction.interaction_type == "save":
                        weight = 0.8
                    elif interaction.interaction_type == "click":
                        weight = 0.3

                    preferences["categories"][interaction.article.category] += weight

                # Update sentiment preference
                if interaction.article.sentiment_score:
                    sentiment_weight = 0.1
                    if interaction.interaction_type == "save":
                        sentiment_weight = 0.5
                    elif interaction.interaction_type == "remove":
                        sentiment_weight = -0.3

                    preferences["sentiment_preference"] += (
                        interaction.article.sentiment_score * sentiment_weight
                    )

        # Normalize sentiment preference
        if interactions:
            preferences["sentiment_preference"] = max(
                -1.0, min(1.0, preferences["sentiment_preference"])
            )

        return preferences

    def _analyze_temporal_patterns(self, interactions: List[UserInteraction]) -> dict:
        """Analyze time-based usage patterns"""
        if not interactions:
            return {"peak_usage_hours": [9, 12, 17], "recency_bias": 0.7}

        hourly_usage = [0] * 24
        for interaction in interactions:
            hour = interaction.timestamp.hour
            hourly_usage[hour] += 1

        # Find peak hours (hours with usage above 70% of max)
        max_usage = max(hourly_usage)
        peak_threshold = max_usage * 0.7
        peak_hours = [
            hour for hour, usage in enumerate(hourly_usage) if usage >= peak_threshold
        ]

        return {
            "peak_usage_hours": peak_hours if peak_hours else [9, 12, 17],
            "hourly_usage": hourly_usage,
            "recency_bias": 0.7,
        }

    def _calculate_engagement_metrics(
        self, interactions: List[UserInteraction]
    ) -> dict:
        """Calculate various engagement metrics"""
        if not interactions:
            return {"avg_time_spent": 30, "click_through_rate": 0.1, "save_rate": 0.05}

        total_time = sum(interaction.duration or 0 for interaction in interactions)
        avg_time = total_time / len(interactions) if interactions else 30

        click_count = sum(1 for i in interactions if i.interaction_type == "click")
        save_count = sum(1 for i in interactions if i.interaction_type == "save")

        return {
            "avg_time_spent": avg_time,
            "click_through_rate": (
                click_count / len(interactions) if interactions else 0.1
            ),
            "save_rate": save_count / len(interactions) if interactions else 0.05,
            "total_interactions": len(interactions),
        }

    def _analyze_content_affinities(self, interactions: List[UserInteraction]) -> dict:
        """Analyze content-based preferences"""
        topic_affinities = {}
        entity_affinities = {"companies": [], "people": []}

        for interaction in interactions:
            if interaction.article and interaction.article.content_analysis:
                try:
                    analysis = json.loads(interaction.article.content_analysis)

                    # Update topic affinities
                    if "topics" in analysis and "primary_topic" in analysis["topics"]:
                        topic = analysis["topics"]["primary_topic"]
                        if topic not in topic_affinities:
                            topic_affinities[topic] = 0

                        weight = 0.1
                        if interaction.interaction_type == "save":
                            weight = 0.8
                        elif interaction.interaction_type == "remove":
                            weight = -0.3

                        topic_affinities[topic] += weight

                    # Update entity affinities
                    if "entities" in analysis:
                        entities = analysis["entities"]
                        if "companies" in entities:
                            for company in entities["companies"]:
                                if company not in entity_affinities["companies"]:
                                    entity_affinities["companies"].append(company)

                except json.JSONDecodeError:
                    continue

        return {
            "topic_affinities": topic_affinities,
            "entity_affinities": entity_affinities,
        }


class RecommendationScoringEngine:
    def __init__(self):
        self.scoring_weights = {
            "content_relevance": 0.35,
            "user_affinity": 0.25,
            "temporal_relevance": 0.20,
            "source_quality": 0.10,
            "diversity_factor": 0.10,
        }

    def calculate_article_score(self, article: Article, user_profile: dict) -> float:
        """Calculate personalized score for an article"""
        try:
            content_analysis = (
                json.loads(article.content_analysis) if article.content_analysis else {}
            )
        except json.JSONDecodeError:
            content_analysis = {}

        scores = {
            "content_relevance": self._calculate_content_relevance(
                article, user_profile, content_analysis
            ),
            "user_affinity": self._calculate_user_affinity(
                article, user_profile, content_analysis
            ),
            "temporal_relevance": self._calculate_temporal_relevance(
                article, user_profile
            ),
            "source_quality": self._calculate_source_quality(article),
            "diversity_factor": self._calculate_diversity_factor(article, user_profile),
        }

        # Weighted sum of all scores
        final_score = sum(
            scores[component] * self.scoring_weights[component] for component in scores
        )

        return final_score

    def _calculate_content_relevance(
        self, article: Article, user_profile: dict, content_analysis: dict
    ) -> float:
        """Calculate how relevant the content is to user preferences"""
        relevance_score = 0.0

        # Check explicit preferences
        user_tickers = user_profile["explicit_preferences"]["tickers"]
        if (
            "entities" in content_analysis
            and "companies" in content_analysis["entities"]
        ):
            article_entities = content_analysis["entities"]["companies"]

            # Direct ticker match
            for ticker in user_tickers:
                if ticker.upper() in [entity.upper() for entity in article_entities]:
                    relevance_score += 0.4

        # Topic affinity
        user_topics = user_profile["content_affinities"]["topic_affinities"]
        if (
            "topics" in content_analysis
            and "primary_topic" in content_analysis["topics"]
        ):
            article_topic = content_analysis["topics"]["primary_topic"]
            if article_topic in user_topics:
                relevance_score += min(user_topics[article_topic], 1.0) * 0.3

        # Sentiment alignment
        user_sentiment_pref = user_profile["implicit_preferences"][
            "sentiment_preference"
        ]
        if article.sentiment_score:
            sentiment_alignment = (
                1 - abs(user_sentiment_pref - article.sentiment_score) / 2
            )
            relevance_score += sentiment_alignment * 0.2

        return min(relevance_score, 1.0)

    def _calculate_user_affinity(
        self, article: Article, user_profile: dict, content_analysis: dict
    ) -> float:
        """Calculate user's historical affinity for similar content"""
        affinity_score = 0.0

        # Source preference
        user_sources = user_profile["explicit_preferences"]["sources"]
        if article.source and article.source.lower() in [
            s.lower() for s in user_sources
        ]:
            affinity_score += 0.3

        # Category preference
        user_categories = user_profile["implicit_preferences"]["categories"]
        if article.category and article.category in user_categories:
            affinity_score += min(user_categories[article.category], 1.0) * 0.4

        return min(affinity_score, 1.0)

    def _calculate_temporal_relevance(
        self, article: Article, user_profile: dict
    ) -> float:
        """Calculate temporal relevance based on user patterns"""
        temporal_score = 0.0

        # Recency bias
        article_age_hours = (time.time() - article.datetime) / 3600
        recency_bias = user_profile["temporal_patterns"]["recency_bias"]

        if article_age_hours < 1:
            temporal_score += recency_bias * 0.4
        elif article_age_hours < 24:
            temporal_score += recency_bias * 0.2

        # Time of day preference
        current_hour = datetime.now().hour
        peak_hours = user_profile["temporal_patterns"]["peak_usage_hours"]

        if current_hour in peak_hours:
            temporal_score += 0.3

        return min(temporal_score, 1.0)

    def _calculate_source_quality(self, article: Article) -> float:
        """Calculate source quality and reliability score"""
        source_quality_scores = {
            "reuters": 0.95,
            "bloomberg": 0.92,
            "financial times": 0.90,
            "wall street journal": 0.88,
            "cnbc": 0.85,
            "marketwatch": 0.80,
            "yahoo finance": 0.75,
        }

        if article.source:
            return source_quality_scores.get(article.source.lower(), 0.5)
        return 0.5

    def _calculate_diversity_factor(
        self, article: Article, user_profile: dict
    ) -> float:
        """Calculate diversity factor to avoid filter bubbles"""
        diversity_score = 1.0

        # Boost score for underrepresented topics
        user_topics = user_profile["content_affinities"]["topic_affinities"]
        if article.category and article.category not in user_topics:
            diversity_score += 0.2

        return max(diversity_score, 0.0)


class LearningAndAdaptationEngine:
    def __init__(self):
        self.learning_rate = 0.1
        self.decay_factor = 0.95
        self.minimum_confidence = 0.3

    def update_user_profile(self, user_id: int, interaction: UserInteraction, db):
        """Update user profile based on new interaction"""
        # This would update the user profile in real-time
        # For now, we'll just log the interaction
        logger.info(
            f"User {user_id} {interaction.interaction_type} article {interaction.article_id}"
        )

    def _calculate_learning_signal(self, interaction: UserInteraction) -> float:
        """Calculate the strength of the learning signal from interaction"""
        base_signals = {
            "click": 0.3,
            "save": 0.8,
            "remove": -0.5,
        }

        base_signal = base_signals.get(interaction.interaction_type, 0.0)

        # Adjust based on duration (time spent)
        if interaction.duration:
            duration_factor = min(interaction.duration / 60, 2.0)  # Cap at 2 minutes
            base_signal *= duration_factor

        return base_signal


class PersonalizationOrchestrator:
    def __init__(self):
        self.profile_engine = UserProfileEngine()
        self.content_analyzer = ContentAnalysisEngine()
        self.scoring_engine = RecommendationScoringEngine()
        self.learning_engine = LearningAndAdaptationEngine()
        self.cache = {}

    def get_personalized_news(self, user_id: int, db, limit: int = 20) -> List[Article]:
        """Main method to get personalized news feed"""

        # Get user profile
        user_profile = self.profile_engine.build_user_profile(user_id, db)

        # Get candidate articles
        candidate_articles = db.query(Article).filter(Article.removed == False).all()

        # Score and rank articles
        scored_articles = []
        for article in candidate_articles:
            score = self.scoring_engine.calculate_article_score(article, user_profile)
            scored_articles.append((article, score))

        # Sort by score and apply diversity
        ranked_articles = self._apply_diversity_filter(scored_articles, limit)

        return [article for article, score in ranked_articles]

    def _apply_diversity_filter(
        self, scored_articles: List[tuple], limit: int
    ) -> List[tuple]:
        """Apply diversity filter to avoid filter bubbles"""
        if len(scored_articles) <= limit:
            return scored_articles

        # Sort by score first
        sorted_articles = sorted(scored_articles, key=lambda x: x[1], reverse=True)

        # Apply diversity penalty
        selected_articles = []
        category_counts = {}

        for article, score in sorted_articles:
            category = article.category or "general"

            # Apply diversity penalty
            diversity_penalty = category_counts.get(category, 0) * 0.1
            adjusted_score = score - diversity_penalty

            # Select article if it's still in top after penalty
            if len(selected_articles) < limit:
                selected_articles.append((article, adjusted_score))
                category_counts[category] = category_counts.get(category, 0) + 1

        return selected_articles


# Initialize consolidated News Intelligence service
news_intelligence = NewsIntelligenceService()

# Initialize personalization orchestrator
personalization_orchestrator = PersonalizationOrchestrator()

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


@app.post("/api/articles/{article_id}/unsave")
def unsave_article(article_id: str, db=Depends(get_db)):
    """Remove article from saved list"""
    db = SessionLocal()
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.saved = False
    db.commit()
    db.close()
    return {"status": "unsaved"}


@app.get("/api/articles/saved", response_model=List[ArticleModel])
def get_saved_articles(db=Depends(get_db)):
    """Get all saved articles"""
    db = SessionLocal()
    saved_articles = db.query(Article).filter(Article.saved == True).all()

    response_articles = []
    for article in saved_articles:
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
                tags=article.tags,
            )
        )

    db.close()
    return response_articles


# Market Data Endpoints


def get_ticker_info(symbol: str) -> TickerInfo:
    """Get comprehensive ticker information from yfinance"""
    try:
        if not YFINANCE_AVAILABLE:
            return {"symbol": symbol, "price": 0.0, "change": 0.0, "changePercent": 0.0}
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get current price and calculate change
        current_price = info.get("currentPrice", 0.0)
        previous_close = info.get("previousClose", 0.0)

        if current_price == 0.0:
            # Fallback to regular market price if currentPrice is not available
            current_price = info.get("regularMarketPrice", 0.0)

        change = current_price - previous_close if previous_close else 0.0
        change_percent = (change / previous_close * 100) if previous_close else 0.0

        return TickerInfo(
            symbol=symbol.upper(),
            name=info.get("longName", symbol),
            current_price=round(current_price, 2),
            previous_close=round(previous_close, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=info.get("volume"),
            market_cap=info.get("marketCap"),
            day_high=info.get("dayHigh"),
            day_low=info.get("dayLow"),
            year_high=info.get("fiftyTwoWeekHigh"),
            year_low=info.get("fiftyTwoWeekLow"),
        )
    except Exception as e:
        logger.error(f"Error fetching ticker info for {symbol}: {e}")
        # Return default ticker info on error
        return TickerInfo(
            symbol=symbol.upper(),
            name=symbol,
            current_price=0.0,
            previous_close=0.0,
            change=0.0,
            change_percent=0.0,
        )


@app.get("/api/market/ticker/{symbol}", response_model=TickerInfo)
@limiter.limit("60/minute")
async def get_ticker(symbol: str, request: Request):
    """Get detailed information for a specific ticker"""
    return get_ticker_info(symbol)


@app.get("/api/market/summary", response_model=MarketSummary)
@limiter.limit("30/minute")
async def get_market_summary(
    request: Request, tickers: str = "AAPL,TSLA,MSFT,GOOGL,AMZN"
):
    """Get market summary for multiple tickers"""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    # Limit to 10 tickers to avoid rate limiting
    ticker_list = ticker_list[:10]

    ticker_infos = []
    for symbol in ticker_list:
        ticker_info = get_ticker_info(symbol)
        ticker_infos.append(ticker_info)

    return MarketSummary(tickers=ticker_infos, last_updated=datetime.now().isoformat())


@app.get("/api/market/user-tickers", response_model=MarketSummary)
@limiter.limit("60/minute")
async def get_user_market_data(request: Request, db=Depends(get_db)):
    """Get market data for user's preferred tickers"""

    # Get or create user (simplified for demo)
    user = db.query(User).filter(User.id == "demo_1").first()
    if not user:
        user = User(
            id="demo_1",
            username="demo_user",
            email="demo@example.com",
            provider="demo",
            provider_id="demo_1",
            trades=json.dumps([]),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get user preferences from trades
    user_tickers = json.loads(user.trades) if user.trades else []
    tickers = user_tickers

    if not tickers:
        # Default tickers if user has no preferences
        tickers = ["AAPL", "TSLA", "MSFT"]

    # Get market data for user's tickers
    ticker_infos = []
    for symbol in tickers[:10]:  # Limit to 10 tickers
        ticker_info = get_ticker_info(symbol)
        ticker_infos.append(ticker_info)

    return MarketSummary(tickers=ticker_infos, last_updated=datetime.now().isoformat())


@app.get("/api/market/search/{query}")
@limiter.limit("30/minute")
async def search_tickers(query: str, request: Request):
    """Search for tickers by company name or symbol"""
    try:
        # Use yfinance search functionality
        if not YFINANCE_AVAILABLE:
            return {"results": []}
        search_results = yf.search(query)

        # Format results
        results = []
        for result in search_results.head(10).iterrows():
            data = result[1]
            results.append(
                {
                    "symbol": data.get("symbol", ""),
                    "name": data.get("longname", ""),
                    "type": data.get("quoteType", ""),
                    "exchange": data.get("exchange", ""),
                }
            )

        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching tickers for query '{query}': {e}")
        return {"results": []}




# SEC Document Endpoints - Added by add_sec_routes.py
try:
    from sec_service import sec_service
    SEC_SERVICE_AVAILABLE = True
except ImportError:
    print("Warning: SEC service not available")
    SEC_SERVICE_AVAILABLE = False

class SECSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 50

class SECDocumentResponse(BaseModel):
    id: str
    title: str
    company: str
    ticker: str
    documentType: str
    filingDate: str
    url: str
    content: Optional[str] = None
    html_content: Optional[str] = None
    highlights: Optional[List[Dict]] = None

@app.post("/api/sec/search")
@limiter.limit("20/minute")
async def search_sec_documents(
    sec_request: SECSearchRequest, 
    request: Request,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Search for SEC documents by company name, ticker, or document type"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")
    
    try:
        logger.info(f"SEC search request: {sec_request.query}")
        
        # Search for documents
        documents = sec_service.search_documents(sec_request.query, sec_request.limit)
        
        # Format response
        response_docs = []
        for doc in documents:
            response_docs.append(SECDocumentResponse(
                id=doc["id"],
                title=doc["title"],
                company=doc["company"],
                ticker=doc["ticker"],
                documentType=doc["documentType"],
                filingDate=doc["filingDate"],
                url=doc["url"]
            ))
        
        return {"documents": response_docs}
        
    except Exception as e:
        logger.error(f"Error in SEC search: {e}")
        raise HTTPException(status_code=500, detail="Failed to search SEC documents")

@app.get("/api/sec/document/{doc_id}")
@limiter.limit("10/minute") 
async def get_sec_document(
    doc_id: str,
    query: Optional[str] = None,
    request: Request = None,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Get full SEC document content with optional query highlighting"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")
        
    try:
        # Parse document ID (format: cik_accession)
        parts = doc_id.split("_", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid document ID format")
        
        cik, accession = parts
        
        # Get document URL
        acc_no_dash = accession.replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}"
        
        # Get filings to find the primary document
        filings_data = sec_service.get_latest_filings(cik)
        if not filings_data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Find the specific filing
        recent = filings_data.get("filings", {}).get("recent", {})
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        
        primary_doc = None
        form_type = None
        filing_date = None
        
        for i, acc in enumerate(accessions):
            if acc == accession:
                primary_doc = docs[i] if i < len(docs) else None
                form_type = forms[i] if i < len(forms) else "Unknown"
                filing_date = dates[i] if i < len(dates) else "Unknown"
                break
        
        if not primary_doc:
            raise HTTPException(status_code=404, detail="Primary document not found")
        
        # Construct full URL
        full_url = f"{doc_url}/{primary_doc}"
        
        # Get document content (both text and HTML)
        content = sec_service.get_document_content(full_url)
        html_content = sec_service.get_document_html(full_url)
        if not content and not html_content:
            raise HTTPException(status_code=404, detail="Failed to retrieve document content")
        
        # Generate highlights if query provided
        highlights = []
        if query:
            highlights = sec_service.search_document_content(content, query)
        
        # Get company name
        company_name = filings_data.get("name", "Unknown Company")
        ticker = sec_service._get_ticker_from_cik(cik)
        
        return SECDocumentResponse(
            id=doc_id,
            title=f"Form {form_type}",
            company=company_name,
            ticker=ticker,
            documentType=form_type,
            filingDate=filing_date,
            url=full_url,
            content=content,
            html_content=html_content,
            highlights=highlights
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SEC document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")

@app.get("/api/sec/company/{ticker}")
@limiter.limit("15/minute")
async def get_company_filings(
    ticker: str,
    limit: Optional[int] = 50,
    request: Request = None,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Get recent SEC filings for a specific company by ticker"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")
        
    try:
        # Get CIK from ticker
        cik = sec_service.get_cik_from_ticker(ticker)
        if not cik:
            raise HTTPException(status_code=404, detail=f"Company not found for ticker: {ticker}")
        
        # Get company filings
        filings = sec_service.get_company_filings(cik, limit=limit)
        
        # Format response
        response_docs = []
        for filing in filings[:limit]:
            response_docs.append(SECDocumentResponse(
                id=filing["id"],
                title=filing["title"],
                company=filing["company"],
                ticker=filing["ticker"],
                documentType=filing["documentType"],
                filingDate=filing["filingDate"],
                url=filing["url"]
            ))
        
        return {"documents": response_docs}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filings for ticker {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve company filings")

# SEC RAG Endpoints - Document-specific RAG search
try:
    from sec_rag_service import sec_rag_service
    SEC_RAG_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("SEC RAG service not available")
    SEC_RAG_SERVICE_AVAILABLE = False

class SECRAGQueryRequest(BaseModel):
    document_id: str
    query: str
    top_k: Optional[int] = 5

class SECRAGResponse(BaseModel):
    answer: str
    chunks: List[Dict]
    document_info: Optional[Dict] = None
    metadata: Optional[Dict] = None
    query: str
    error: Optional[str] = None

@app.post("/api/sec/rag/query")
@limiter.limit("10/minute")
async def query_sec_document_rag(
    rag_request: SECRAGQueryRequest,
    request: Request,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Query a SEC document using RAG (Retrieval-Augmented Generation)"""
    if not SEC_RAG_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC RAG service not available")
    
    try:
        logger.info(f"SEC RAG query for document {rag_request.document_id}: {rag_request.query}")
        
        # First, ensure document is processed
        document_processed = await sec_rag_service.process_document(rag_request.document_id)
        if not document_processed:
            raise HTTPException(status_code=500, detail="Failed to process document for RAG")
        
        # Query the document
        result = sec_rag_service.query_document(rag_request.document_id, rag_request.query, rag_request.top_k)
        
        return SECRAGResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in SEC RAG query: {e}")
        raise HTTPException(status_code=500, detail="Failed to process RAG query")

@app.post("/api/sec/rag/process/{doc_id}")
@limiter.limit("5/minute")
async def process_sec_document_for_rag(
    doc_id: str,
    request: Request,
    force_refresh: Optional[bool] = False,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Process a SEC document for RAG queries"""
    if not SEC_RAG_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC RAG service not available")
    
    try:
        logger.info(f"Processing SEC document for RAG: {doc_id}")
        
        success = await sec_rag_service.process_document(doc_id, force_refresh=force_refresh)
        
        if success:
            status_info = sec_rag_service.get_document_status(doc_id)
            return {
                "status": "success",
                "document_id": doc_id,
                "message": f"Document processed successfully into {status_info['chunk_count']} chunks",
                **status_info
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process document")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document for RAG")

@app.get("/api/sec/rag/status/{doc_id}")
@limiter.limit("20/minute")
async def get_sec_document_rag_status(
    doc_id: str,
    request: Request,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Get RAG processing status for a SEC document"""
    if not SEC_RAG_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC RAG service not available")
    
    try:
        status_info = sec_rag_service.get_document_status(doc_id)
        return {
            "document_id": doc_id,
            **status_info
        }
        
    except Exception as e:
        logger.error(f"Error getting RAG status for document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document status")


# Create database tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
