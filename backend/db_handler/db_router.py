"""
Database Router Module
Contains all database-related FastAPI endpoints for articles and user interactions.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import ticker validation utilities
from ticker_validator import validate_ticker_list

logger = logging.getLogger(__name__)

# Initialize rate limiter (will use the same one from main app)
limiter = Limiter(key_func=get_remote_address)

# Pydantic Models
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

# Article Management Functions
async def save_article(article_id: str, db: Session, Article):
    """Save an article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.saved = True
    article.removed = False
    db.commit()
    return {"status": "saved"}

async def remove_article(article_id: str, db: Session, Article):
    """Remove an article"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.removed = True
    article.saved = False
    db.commit()
    return {"status": "removed"}

async def unsave_article(article_id: str, db: Session, Article):
    """Remove article from saved list"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.saved = False
    db.commit()
    return {"status": "unsaved"}

async def get_saved_articles(db: Session, Article):
    """Get all saved articles"""
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

    return response_articles

async def get_saved_legacy(db: Session, Article):
    """Legacy saved articles endpoint"""
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

# User Management Functions
async def record_interaction(interaction: InteractionModel, db: Session, User, UserInteraction):
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
        timestamp=datetime.now(timezone.utc),
    )

    db.add(new_interaction)
    db.commit()

    return {"status": "recorded"}

async def get_user(db: Session, User):
    """Get user information"""
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

async def update_user(user_data: UserModel, db: Session, User):
    """Update user information"""
    validation_result = validate_ticker_list(user_data.trades)

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

    user.trades = str(validation_result["valid_tickers"])
    db.commit()
    db.refresh(user)

    response_data = {
        "username": user.username,
        "email": user.email,
        "trades": eval(user.trades) if user.trades else [],
    }

    if validation_result["invalid_tickers"] or validation_result["warnings"]:
        response_data["validation"] = {
            "rejected_tickers": validation_result["invalid_tickers"],
            "warnings": validation_result["warnings"],
        }

    return response_data

# Function to add all database routes to the FastAPI app
def add_db_routes(app, limiter_instance, get_db_func, Article_model, User_model, UserInteraction_model):
    """
    Add all database routes to the FastAPI app

    Args:
        app: FastAPI application instance
        limiter_instance: Rate limiter instance from main app
        get_db_func: Database dependency function
        Article_model: Article SQLAlchemy model
        User_model: User SQLAlchemy model
        UserInteraction_model: UserInteraction SQLAlchemy model
    """
    global limiter
    limiter = limiter_instance

    # Article management endpoints
    @app.post("/api/articles/{article_id}/save")
    async def save_article_endpoint(article_id: str, db: Session = Depends(get_db_func)):
        """Save an article"""
        return await save_article(article_id, db, Article_model)

    @app.post("/api/articles/{article_id}/remove")
    async def remove_article_endpoint(article_id: str, db: Session = Depends(get_db_func)):
        """Remove an article"""
        return await remove_article(article_id, db, Article_model)

    @app.post("/api/articles/{article_id}/unsave")
    async def unsave_article_endpoint(article_id: str, db: Session = Depends(get_db_func)):
        """Remove article from saved list"""
        return await unsave_article(article_id, db, Article_model)

    @app.get("/api/articles/saved", response_model=List[ArticleModel])
    async def get_saved_articles_endpoint(db: Session = Depends(get_db_func)):
        """Get all saved articles"""
        return await get_saved_articles(db, Article_model)

    @app.get("/api/saved", response_model=List[ArticleModel])
    async def get_saved_legacy_endpoint(db: Session = Depends(get_db_func)):
        """Legacy saved articles endpoint"""
        return await get_saved_legacy(db, Article_model)

    # User and interaction endpoints
    @app.post("/api/interactions")
    async def record_interaction_endpoint(interaction: InteractionModel, db: Session = Depends(get_db_func)):
        """Record user interaction for learning"""
        return await record_interaction(interaction, db, User_model, UserInteraction_model)

    @app.get("/api/user", response_model=UserModel)
    async def get_user_endpoint(db: Session = Depends(get_db_func)):
        """Get user information"""
        return await get_user(db, User_model)

    @app.post("/api/user", response_model=UserModel)
    async def update_user_endpoint(user_data: UserModel, db: Session = Depends(get_db_func)):
        """Update user information"""
        return await update_user(user_data, db, User_model)

    logger.info(" Database routes added to FastAPI app")