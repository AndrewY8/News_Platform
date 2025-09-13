"""
Enhanced Pipeline Integration Service

This service integrates the Enhanced News Discovery Pipeline with the existing
FastAPI backend, providing seamless access to the multi-stage news discovery
through the existing /api/chat endpoint.
"""

import logging
import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import the enhanced pipeline
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from enhanced_news_pipeline import create_enhanced_news_pipeline, EnhancedNewsDiscoveryPipeline

# Import existing services
from news_intelligence import NewsIntelligenceService

logger = logging.getLogger(__name__)


class EnhancedPipelineNewsService:
    """
    Enhanced news service that integrates the multi-stage discovery pipeline
    with the existing news intelligence system.
    """

    def __init__(self, gemini_api_key: str, tavily_api_key: str, newsapi_key: str):
        """
        Initialize the enhanced pipeline news service.

        Args:
            gemini_api_key: API key for Gemini AI
            tavily_api_key: API key for Tavily search
            newsapi_key: API key for NewsAPI (fallback)
        """
        self.gemini_api_key = gemini_api_key
        self.tavily_api_key = tavily_api_key
        self.newsapi_key = newsapi_key

        # Initialize the enhanced pipeline
        self.pipeline = None
        self.pipeline_available = False

        # Initialize fallback news intelligence service
        self.news_intelligence = NewsIntelligenceService()

        # Try to initialize the enhanced pipeline
        self._initialize_enhanced_pipeline()

        logger.info(f"EnhancedPipelineNewsService initialized (pipeline: {self.pipeline_available})")

    def _initialize_enhanced_pipeline(self):
        """Initialize the enhanced news discovery pipeline."""
        try:
            if self.gemini_api_key and self.tavily_api_key:
                self.pipeline = create_enhanced_news_pipeline(
                    gemini_api_key=self.gemini_api_key,
                    tavily_api_key=self.tavily_api_key,
                    max_retrievers=5
                )
                self.pipeline_available = True
                logger.info("✅ Enhanced pipeline initialized successfully")
            else:
                logger.warning("⚠️ Missing API keys for enhanced pipeline")

        except Exception as e:
            logger.error(f"❌ Failed to initialize enhanced pipeline: {e}")
            self.pipeline_available = False

    async def generate_enhanced_chat_response(self,
                                            message: str,
                                            user_tickers: List[str] = None,
                                            use_enhanced_pipeline: bool = True,
                                            conversation_history: List = None) -> Dict[str, Any]:
        """
        Generate enhanced chat response using the multi-stage pipeline or fallback.

        Args:
            message: User's message/query
            user_tickers: User's tracked tickers
            use_enhanced_pipeline: Whether to use the enhanced pipeline
            conversation_history: Previous conversation context

        Returns:
            Enhanced chat response with articles and metadata
        """
        start_time = datetime.now()
        user_tickers = user_tickers or []

        try:
            # Decide whether to use enhanced pipeline
            should_use_pipeline = (
                use_enhanced_pipeline and
                self.pipeline_available and
                self._should_use_pipeline_for_query(message)
            )

            if should_use_pipeline:
                logger.info(f"🚀 Using enhanced pipeline for: '{message}'")
                return await self._generate_enhanced_pipeline_response(
                    message, user_tickers, conversation_history
                )
            else:
                logger.info(f"📰 Using fallback intelligence for: '{message}'")
                return await self._generate_fallback_response(
                    message, user_tickers, conversation_history
                )

        except Exception as e:
            logger.error(f"❌ Enhanced chat response failed: {e}")

            # Ultimate fallback
            return await self._generate_fallback_response(
                message, user_tickers, conversation_history
            )

    def _should_use_pipeline_for_query(self, message: str) -> bool:
        """
        Determine if a query should use the enhanced pipeline.

        Args:
            message: User's message

        Returns:
            True if should use pipeline, False otherwise
        """
        # Use pipeline for news-related queries
        news_indicators = [
            'news', 'latest', 'update', 'report', 'announce', 'develop',
            'earnings', 'financial', 'market', 'stock', 'revenue', 'profit',
            'merger', 'acquisition', 'ipo', 'sec filing', 'quarter',
            'breaking', 'recent', 'today', 'yesterday', 'week', 'month'
        ]

        message_lower = message.lower()
        return any(indicator in message_lower for indicator in news_indicators)

    async def _generate_enhanced_pipeline_response(self,
                                                 message: str,
                                                 user_tickers: List[str],
                                                 conversation_history: List) -> Dict[str, Any]:
        """
        Generate response using the enhanced multi-stage pipeline.

        Args:
            message: User's message
            user_tickers: User's tracked tickers
            conversation_history: Previous conversation context

        Returns:
            Enhanced response with curated articles
        """
        try:
            # Prepare user preferences
            user_preferences = {
                'watchlist': user_tickers,
                'topics': self._extract_topics_from_message(message),
                'keywords': self._extract_keywords_from_message(message)
            }

            # Run the enhanced pipeline
            pipeline_results = await self.pipeline.discover_news(message, user_preferences)

            if pipeline_results['processing_stats']['success']:
                # Generate AI response based on pipeline results
                ai_response = await self._generate_ai_response_from_pipeline(
                    message, pipeline_results, user_tickers
                )

                # Format for frontend
                formatted_response = self._format_pipeline_response(
                    ai_response, pipeline_results, message
                )

                return formatted_response

            else:
                # Pipeline failed, use fallback
                logger.warning("Pipeline execution failed, using fallback")
                return await self._generate_fallback_response(message, user_tickers, conversation_history)

        except Exception as e:
            logger.error(f"Enhanced pipeline response failed: {e}")
            return await self._generate_fallback_response(message, user_tickers, conversation_history)

    async def _generate_fallback_response(self,
                                        message: str,
                                        user_tickers: List[str],
                                        conversation_history: List) -> Dict[str, Any]:
        """
        Generate response using the fallback news intelligence service.

        Args:
            message: User's message
            user_tickers: User's tracked tickers
            conversation_history: Previous conversation context

        Returns:
            Fallback response using traditional method
        """
        try:
            # Use existing news intelligence service
            response = await self.news_intelligence.generate_chat_response(
                message, user_tickers, conversation_history or []
            )

            # Add metadata to indicate fallback usage
            if isinstance(response, dict):
                response['search_method'] = 'fallback_intelligence'
                response['enhanced_pipeline_used'] = False

            return response

        except Exception as e:
            logger.error(f"Fallback response also failed: {e}")
            return {
                "response": "I'm having trouble processing your request right now. Please try again later.",
                "suggested_articles": [],
                "success": False,
                "search_method": "error_fallback",
                "enhanced_pipeline_used": False,
                "error": str(e)
            }

    def _extract_topics_from_message(self, message: str) -> List[str]:
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

    def _extract_keywords_from_message(self, message: str) -> List[str]:
        """Extract keywords from user message."""
        # Simple keyword extraction
        financial_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'growth', 'decline',
            'merger', 'acquisition', 'ipo', 'sec filing', 'quarterly',
            'annual', 'guidance', 'outlook', 'forecast'
        ]

        message_lower = message.lower()
        keywords = [kw for kw in financial_keywords if kw in message_lower]

        return keywords

    async def _generate_ai_response_from_pipeline(self,
                                                message: str,
                                                pipeline_results: Dict,
                                                user_tickers: List[str]) -> str:
        """
        Generate AI response based on pipeline results.

        Args:
            message: Original user message
            pipeline_results: Results from enhanced pipeline
            user_tickers: User's tracked tickers

        Returns:
            AI-generated response string
        """
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

            # Use Gemini to generate response
            response = await self.news_intelligence.generate_chat_response_with_context(
                message, context, user_tickers
            )

            return response

        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return f"Based on my analysis of recent news, I found several relevant insights about your query: {message}"

    def _format_pipeline_response(self,
                                ai_response: str,
                                pipeline_results: Dict,
                                original_message: str) -> Dict[str, Any]:
        """
        Format the pipeline response for frontend consumption.

        Args:
            ai_response: AI-generated response text
            pipeline_results: Raw pipeline results
            original_message: Original user message

        Returns:
            Formatted response dictionary
        """
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
            "response": ai_response if isinstance(ai_response, str) else ai_response.get('response', ''),
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

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and health."""
        stats = {
            "pipeline_available": self.pipeline_available,
            "gemini_configured": bool(self.gemini_api_key),
            "tavily_configured": bool(self.tavily_api_key),
            "fallback_available": self.news_intelligence is not None
        }

        if self.pipeline:
            stats.update(self.pipeline.get_pipeline_stats())

        return stats

    def cleanup(self):
        """Cleanup service resources."""
        try:
            if self.pipeline:
                self.pipeline.cleanup()
            logger.info("Enhanced pipeline service cleanup completed")
        except Exception as e:
            logger.error(f"Error during service cleanup: {e}")


# Global service instance
_enhanced_pipeline_service = None


def get_enhanced_pipeline_news_service() -> EnhancedPipelineNewsService:
    """
    Get the global enhanced pipeline news service instance.

    Returns:
        EnhancedPipelineNewsService instance
    """
    global _enhanced_pipeline_service

    if _enhanced_pipeline_service is None:
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        newsapi_key = os.getenv("News_API_KEY", "")

        _enhanced_pipeline_service = EnhancedPipelineNewsService(
            gemini_api_key=gemini_key,
            tavily_api_key=tavily_key,
            newsapi_key=newsapi_key
        )

    return _enhanced_pipeline_service


def initialize_enhanced_pipeline_service():
    """Initialize the enhanced pipeline service at startup."""
    try:
        service = get_enhanced_pipeline_news_service()
        stats = service.get_service_stats()
        logger.info(f"Enhanced pipeline service initialized: {stats}")
        return service
    except Exception as e:
        logger.error(f"Failed to initialize enhanced pipeline service: {e}")
        return None


# Example usage and testing
async def test_enhanced_integration():
    """Test the enhanced pipeline integration."""
    from dotenv import load_dotenv
    load_dotenv()

    service = get_enhanced_pipeline_news_service()

    test_queries = [
        "Latest Tesla autonomous driving news",
        "Microsoft AI developments",
        "Apple earnings report"
    ]

    user_tickers = ['TSLA', 'MSFT', 'AAPL']

    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")

        try:
            result = await service.generate_enhanced_chat_response(
                message=query,
                user_tickers=user_tickers,
                use_enhanced_pipeline=True
            )

            print(f"✅ Success: {result.get('success', False)}")
            print(f"📊 Method: {result.get('search_method', 'unknown')}")
            print(f"📰 Articles: {len(result.get('suggested_articles', []))}")
            print(f"⏱️  Duration: {result.get('processing_time', 0):.2f}s")

        except Exception as e:
            print(f"❌ Test failed: {e}")

    # Cleanup
    service.cleanup()


if __name__ == "__main__":
    asyncio.run(test_enhanced_integration())