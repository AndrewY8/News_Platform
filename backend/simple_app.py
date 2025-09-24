"""
Simplified Backend for Testing Frontend-Backend Integration
This version works without complex dependencies and provides basic functionality.
"""

import os
import time
import json
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# FastAPI app setup
app = FastAPI(title="News Platform Backend", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS setup
cors_origins = ["http://localhost:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List] = []

class EnhancedSearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    use_agent: bool = True
    limit: int = 10

# Sample data
def get_sample_articles():
    return [
        {
            "id": "sample-1",
            "date": "Today",
            "title": "Market Update: Tech Stocks Show Strong Performance",
            "source": "Financial News",
            "preview": "Technology stocks continued their upward trend as earnings reports exceed expectations across major companies...",
            "sentiment": "positive",
            "tags": ["AAPL", "MSFT", "GOOGL", "TECH"],
            "url": "https://example.com/article1",
            "relevance_score": 0.9,
            "category": "Technology"
        },
        {
            "id": "sample-2",
            "date": "Today",
            "title": "Federal Reserve Maintains Current Interest Rate",
            "source": "Economic Times",
            "preview": "The Federal Reserve announced its decision to maintain the current interest rate, citing stable economic indicators...",
            "sentiment": "neutral",
            "tags": ["FED", "RATES", "ECONOMY"],
            "url": "https://example.com/article2",
            "relevance_score": 0.8,
            "category": "Economy"
        },
        {
            "id": "sample-3",
            "date": "Today",
            "title": "Cryptocurrency Market Sees Mixed Trading",
            "source": "Crypto Daily",
            "preview": "Bitcoin and Ethereum show different directions as market sentiment remains uncertain following regulatory news...",
            "sentiment": "neutral",
            "tags": ["BTC", "ETH", "CRYPTO"],
            "url": "https://example.com/article3",
            "relevance_score": 0.7,
            "category": "Cryptocurrency"
        },
        {
            "id": "sample-4",
            "date": "Yesterday",
            "title": "Oil Prices Rise on Supply Concerns",
            "source": "Energy Report",
            "preview": "Crude oil prices increased by 3% following reports of potential supply disruptions in key producing regions...",
            "sentiment": "positive",
            "tags": ["OIL", "ENERGY", "COMMODITIES"],
            "url": "https://example.com/article4",
            "relevance_score": 0.6,
            "category": "Energy"
        },
        {
            "id": "sample-5",
            "date": "Yesterday",
            "title": "Healthcare Sector Faces New Regulatory Changes",
            "source": "Health Business",
            "preview": "New healthcare regulations could impact pharmaceutical companies and insurance providers in the coming quarter...",
            "sentiment": "negative",
            "tags": ["HEALTHCARE", "REGULATION", "PHARMA"],
            "url": "https://example.com/article5",
            "relevance_score": 0.5,
            "category": "Healthcare"
        }
    ]

# API Endpoints

@app.get("/")
async def root():
    return {"message": "News Platform Backend API", "status": "running"}

@app.get("/api/articles")
@limiter.limit("30/minute")
async def get_articles(request: Request):
    """Get personalized articles"""
    logger.info("Getting personalized articles")
    articles = get_sample_articles()
    return JSONResponse(content=articles[:10])

@app.get("/api/articles/top")
@limiter.limit("30/minute")
async def get_top_articles(request: Request):
    """Get top articles"""
    logger.info("Getting top articles")
    articles = get_sample_articles()
    # Sort by relevance score
    sorted_articles = sorted(articles, key=lambda x: x['relevance_score'], reverse=True)
    return JSONResponse(content=sorted_articles[:15])

@app.get("/api/articles/search")
@limiter.limit("20/minute")
async def search_articles(q: str, request: Request):
    """Search articles"""
    logger.info(f"Searching articles for: {q}")
    articles = get_sample_articles()

    # Simple search filtering by title and preview
    filtered_articles = []
    query_lower = q.lower()
    for article in articles:
        if (query_lower in article['title'].lower() or
            query_lower in article['preview'].lower() or
            any(query_lower in tag.lower() for tag in article['tags'])):
            filtered_articles.append(article)

    return JSONResponse(content=filtered_articles[:20])

@app.post("/api/search/enhanced")
@limiter.limit("10/minute")
async def enhanced_search(req: Request, request: EnhancedSearchRequest):
    """Enhanced search endpoint"""
    logger.info(f"Enhanced search for: {request.query}")

    articles = get_sample_articles()

    # Simple filtering based on query
    filtered_articles = []
    query_lower = request.query.lower()
    for article in articles:
        if (query_lower in article['title'].lower() or
            query_lower in article['preview'].lower() or
            any(query_lower in tag.lower() for tag in article['tags'])):
            filtered_articles.append(article)

    # Limit results
    if request.limit and len(filtered_articles) > request.limit:
        filtered_articles = filtered_articles[:request.limit]

    return JSONResponse(content={
        "success": True,
        "articles": filtered_articles,
        "search_method": "simple_filter",
        "sources_used": ["Sample Data"],
        "total_found": len(filtered_articles)
    })

@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat_endpoint(req: Request, request: ChatRequest):
    """Chat endpoint"""
    logger.info(f"Chat request: {request.message}")

    # Simple response based on keywords
    message_lower = request.message.lower()

    if any(word in message_lower for word in ['tech', 'technology', 'apple', 'microsoft']):
        response_text = "I found some interesting technology news for you. Tech stocks have been performing well recently, with companies like Apple and Microsoft showing strong earnings."
        suggested_articles = [article for article in get_sample_articles() if article['category'] == 'Technology'][:3]
    elif any(word in message_lower for word in ['market', 'economy', 'fed', 'rate']):
        response_text = "Here's what I found about market and economic news. The Federal Reserve's recent decisions continue to impact market sentiment."
        suggested_articles = [article for article in get_sample_articles() if article['category'] == 'Economy'][:3]
    elif any(word in message_lower for word in ['crypto', 'bitcoin', 'ethereum']):
        response_text = "The cryptocurrency market has been showing mixed signals lately. Here are some relevant articles I found."
        suggested_articles = [article for article in get_sample_articles() if article['category'] == 'Cryptocurrency'][:3]
    else:
        response_text = "I've gathered some recent financial news that might interest you. Let me know if you'd like me to focus on any specific sector."
        suggested_articles = get_sample_articles()[:3]

    return JSONResponse(content={
        "response": response_text,
        "suggested_articles": suggested_articles
    })

@app.get("/api/chat/history")
@limiter.limit("30/minute")
async def get_chat_history(request: Request):
    """Get chat history"""
    return JSONResponse(content=[])

@app.post("/api/chat/history")
@limiter.limit("30/minute")
async def save_chat_history(request: Request):
    """Save chat history"""
    return JSONResponse(content={"success": True})

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting News Platform Backend...")
    print("📍 Backend running at: http://localhost:8004")
    print("🔗 Frontend should be at: http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8004)