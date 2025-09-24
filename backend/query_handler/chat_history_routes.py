"""
Chat History Routes Module
Contains all chat history related FastAPI endpoints.
"""

import time
import logging
from datetime import datetime
from fastapi import Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Initialize rate limiter (will use the same one from main app)
limiter = Limiter(key_func=get_remote_address)

# Chat History Route Functions
async def get_chat_history(request: Request, db: Session, ChatHistory):
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

async def save_chat_history(request: Request, db: Session, ChatHistory):
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

async def delete_chat_history(query_id: str, request: Request, db: Session, ChatHistory):
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

# Function to add chat history routes to FastAPI app
def add_chat_history_routes(app, shared_limiter, get_db, ChatHistory):
    """Add chat history routes to the FastAPI app"""

    @app.get("/api/chat/history")
    @shared_limiter.limit("10/minute")
    async def get_chat_history_endpoint(request: Request, db: Session = Depends(get_db)):
        return await get_chat_history(request, db, ChatHistory)

    @app.post("/api/chat/history")
    @shared_limiter.limit("20/minute")
    async def save_chat_history_endpoint(request: Request, db: Session = Depends(get_db)):
        return await save_chat_history(request, db, ChatHistory)

    @app.delete("/api/chat/history/{query_id}")
    @shared_limiter.limit("10/minute")
    async def delete_chat_history_endpoint(query_id: str, request: Request, db: Session = Depends(get_db)):
        return await delete_chat_history(query_id, request, db, ChatHistory)

    logger.info("Chat history routes added successfully")