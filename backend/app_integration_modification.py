"""
FastAPI App Integration Modification

This file shows how to modify your existing app.py to integrate the Enhanced
Pipeline News Service. Add these changes to your backend/app.py file.
"""

# Add these imports at the top of your app.py file
from enhanced_pipeline_integration import (
    get_enhanced_pipeline_news_service,
    initialize_enhanced_pipeline_service
)

# Add this initialization after your existing service initializations
# (around line 70-80 in your app.py, after loading environment variables)

def setup_enhanced_pipeline_service():
    """Setup the enhanced pipeline service at startup."""
    try:
        logger.info("🚀 Initializing Enhanced Pipeline Service...")
        enhanced_service = initialize_enhanced_pipeline_service()

        if enhanced_service:
            stats = enhanced_service.get_service_stats()
            logger.info(f"✅ Enhanced Pipeline Service initialized: {stats}")
            return enhanced_service
        else:
            logger.warning("⚠️ Enhanced Pipeline Service initialization failed, using fallback")
            return None

    except Exception as e:
        logger.error(f"❌ Enhanced Pipeline Service setup failed: {e}")
        return None

# Initialize the enhanced service (add this after line ~80 in your app.py)
enhanced_pipeline_service = setup_enhanced_pipeline_service()

# Modify your existing /api/chat endpoint (around line 1754)
# Replace the existing chat endpoint with this enhanced version:

@app.post("/api/chat")
async def enhanced_chat_about_news(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Enhanced chat endpoint with multi-stage news discovery pipeline.

    This endpoint now supports:
    1. Enhanced pipeline for news queries (multi-stage discovery)
    2. Fallback to existing news intelligence
    3. Traditional chat for non-news queries
    """

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

        # Try enhanced pipeline service first
        if enhanced_pipeline_service:
            try:
                logger.info("🚀 Using Enhanced Pipeline Service")

                chat_result = await enhanced_pipeline_service.generate_enhanced_chat_response(
                    message=request.message,
                    user_tickers=user_tickers,
                    use_enhanced_pipeline=True,
                    conversation_history=request.conversation_history or []
                )

                if chat_result.get("success"):
                    logger.info(f"✅ Enhanced pipeline response generated successfully")
                    logger.info(f"🔍 Search method: {chat_result.get('search_method', 'unknown')}")

                    # Add enhanced metadata
                    chat_result['enhanced_pipeline_available'] = True

                    if chat_result.get('pipeline_metadata'):
                        logger.info(f"📊 Pipeline stats: {chat_result['pipeline_metadata']}")

                    return chat_result
                else:
                    logger.warning(f"Enhanced pipeline returned unsuccessful result")

            except Exception as e:
                logger.error(f"Enhanced pipeline failed: {e}")
                # Continue to fallback

        # Fallback to original simple agent service
        logger.info("📰 Falling back to Simple Agent Service")
        agent_service = get_simple_agent_news_service()

        chat_result = await agent_service.generate_enhanced_chat_response(
            request.message,
            user_tickers,
            use_agent_search=True
        )

        if chat_result.get("success"):
            logger.info(f"✅ Simple agent response generated successfully")
            logger.info(f"🔍 Search method: {chat_result.get('search_method', 'unknown')}")

            # Add metadata to indicate fallback usage
            chat_result['enhanced_pipeline_available'] = enhanced_pipeline_service is not None
            chat_result['used_fallback'] = True

            if chat_result.get('sources_used'):
                logger.info(f"📊 Agent sources used: {chat_result['sources_used']}")

            return chat_result
        else:
            # Ultimate fallback to traditional method
            logger.warning(f"Simple agent failed, falling back to traditional method: {chat_result.get('error')}")

            fallback_result = await news_intelligence.generate_chat_response(
                request.message, user_tickers, request.conversation_history or []
            )

            # Add metadata
            if isinstance(fallback_result, dict):
                fallback_result['enhanced_pipeline_available'] = enhanced_pipeline_service is not None
                fallback_result['used_traditional_fallback'] = True
                fallback_result['search_method'] = 'traditional_intelligence'

            return fallback_result

    except Exception as e:
        logger.error(f"All chat methods failed: {str(e)}")
        return {
            "response": "I'm experiencing technical difficulties. Please try again later.",
            "suggested_articles": [],
            "success": False,
            "error": str(e),
            "enhanced_pipeline_available": enhanced_pipeline_service is not None,
            "search_method": "error_fallback"
        }

# Add new endpoint for pipeline statistics (optional)
@app.get("/api/pipeline/stats")
async def get_pipeline_stats():
    """Get enhanced pipeline statistics and health status."""
    try:
        if enhanced_pipeline_service:
            stats = enhanced_pipeline_service.get_service_stats()
            stats['service_available'] = True
            return stats
        else:
            return {
                "service_available": False,
                "pipeline_available": False,
                "message": "Enhanced pipeline service not initialized"
            }
    except Exception as e:
        return {
            "service_available": False,
            "pipeline_available": False,
            "error": str(e)
        }

# Add cleanup function for graceful shutdown
@app.on_event("shutdown")
async def shutdown_enhanced_services():
    """Cleanup enhanced services on shutdown."""
    try:
        if enhanced_pipeline_service:
            enhanced_pipeline_service.cleanup()
            logger.info("✅ Enhanced pipeline service cleaned up")
    except Exception as e:
        logger.error(f"❌ Error during enhanced service cleanup: {e}")

# Frontend Integration Instructions:
"""
FRONTEND INTEGRATION:

1. The existing frontend chat interface will automatically work with the enhanced pipeline
2. No changes needed to the API call structure
3. Enhanced responses will include additional metadata:

Response format:
{
    "response": "AI generated response",
    "suggested_articles": [...],  // Enhanced curated articles
    "success": true,
    "search_method": "enhanced_pipeline",  // or "fallback_intelligence"
    "enhanced_pipeline_used": true,
    "pipeline_metadata": {
        "total_duration": 12.5,
        "stages_completed": 4,
        "final_article_count": 15,
        "key_points_extracted": 6
    },
    "sources_used": ["reuters.com", "bloomberg.com", "cnbc.com"],
    "processing_time": 12.5
}

3. Frontend can optionally display pipeline metadata to show the enhanced processing
4. Articles will be higher quality and more focused due to the multi-stage process
"""

# Environment Variables Required:
"""
Add to your .env file:

GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

The enhanced pipeline will automatically fall back to existing services if these are missing.
"""

# Testing the Integration:
"""
To test the enhanced integration:

1. Add the above modifications to your app.py
2. Ensure GEMINI_API_KEY and TAVILY_API_KEY are in your .env
3. Start your backend: python app.py
4. Test with frontend chat or direct API calls
5. Check logs for pipeline usage indicators (🚀, 📰, ✅, etc.)

Example test queries that will trigger the enhanced pipeline:
- "Latest Tesla news"
- "Microsoft AI developments"
- "Apple earnings report"
- "Amazon quarterly results"
"""