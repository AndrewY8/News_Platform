"""
User Routes Module
Contains all user management related FastAPI endpoints.
"""

import logging
from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Initialize rate limiter (will use the same one from main app)
limiter = Limiter(key_func=get_remote_address)

# User Route Functions
async def update_user(request: Request, db: Session, User):
    """Update user preferences"""
    try:
        data = await request.json()
        # For now just return success since we don't have user management
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})

async def save_article(article_id: str, request: Request, db: Session, Article):
    """Save an article"""
    try:
        # Update article as saved in database
        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.saved = True
            db.commit()

        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error saving article: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})

async def unsave_article(article_id: str, request: Request, db: Session, Article):
    """Unsave an article"""
    try:
        # Update article as not saved in database
        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.saved = False
            db.commit()

        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error unsaving article: {e}")
        return JSONResponse(content={"success": False, "error": str(e)})

# Function to add user routes to FastAPI app
def add_user_routes(app, shared_limiter, get_db, User, Article):
    """Add user management routes to the FastAPI app"""

    @app.post("/api/user")
    @shared_limiter.limit("10/minute")
    async def update_user_endpoint(request: Request, db: Session = Depends(get_db)):
        return await update_user(request, db, User)

    @app.post("/api/articles/{article_id}/save")
    @shared_limiter.limit("20/minute")
    async def save_article_endpoint(article_id: str, request: Request, db: Session = Depends(get_db)):
        return await save_article(article_id, request, db, Article)

    @app.post("/api/articles/{article_id}/unsave")
    @shared_limiter.limit("20/minute")
    async def unsave_article_endpoint(article_id: str, request: Request, db: Session = Depends(get_db)):
        return await unsave_article(article_id, request, db, Article)

    logger.info("User routes added successfully")