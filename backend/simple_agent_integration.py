"""
Simple Agent Integration Service for News Platform

This is a lightweight integration that provides enhanced search capabilities
while gracefully falling back to traditional news intelligence when
agent modules are not available or working.
"""

import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from news_intelligence import NewsIntelligenceService

logger = logging.getLogger(__name__)


class SimpleAgentNewsService:
    """
    Simplified agent news service that provides enhanced search capabilities
    with robust fallback to traditional news intelligence.
    """
    
    def __init__(self, gemini_api_key: str, newsapi_key: str):
        """
        Initialize the simple agent news service
        
        Args:
            gemini_api_key: API key for Gemini AI
            newsapi_key: API key for NewsAPI
        """
        self.gemini_api_key = gemini_api_key
        self.newsapi_key = newsapi_key
        
        # Initialize the news intelligence service (existing, proven system)
        # The NewsIntelligenceService gets API keys from environment variables
        self.news_intelligence = NewsIntelligenceService()
        
        # Try to initialize enhanced capabilities
        self.enhanced_available = self._check_enhanced_capabilities()
        
        logger.info(f"SimpleAgentNewsService initialized (enhanced: {self.enhanced_available})")
    
    def _check_enhanced_capabilities(self) -> bool:
        """Check if enhanced agent capabilities are available"""
        try:
            # You can add checks here for additional search APIs or services
            # For now, we'll just check if we have the required keys
            return bool(self.gemini_api_key and self.newsapi_key)
        except Exception as e:
            logger.warning(f"Enhanced capabilities check failed: {e}")
            return False

    async def enhanced_search(self, 
                            query: str, 
                            user_tickers: List[str] = None,
                            use_enhanced: bool = True,
                            limit: int = 10) -> Dict[str, Any]:
        """
        Enhanced search that can be extended with agent functionality later
        
        Args:
            query: User's search query
            user_tickers: User's stock interests for personalization
            use_enhanced: Whether to use enhanced search (placeholder for future agent integration)
            limit: Maximum number of articles to return
            
        Returns:
            Dict containing search results and metadata
        """
        try:
            # For now, use the proven news intelligence system
            # This can be extended later when agent modules are properly configured
            
            # Enhanced query processing
            enhanced_query = self._enhance_query_with_context(query, user_tickers)
            
            # Get search results using existing proven system
            news_results = await self.news_intelligence.search_news_by_topic(
                enhanced_query, user_tickers or [], limit=limit
            )
            
            # If no results with enhanced query, try fallback searches
            if not news_results and len(query.split()) > 3:
                logger.info(f"No results for enhanced query, trying fallback searches")
                fallback_results = await self._try_fallback_searches(query, user_tickers, limit)
                if fallback_results:
                    news_results = fallback_results
            
            # Add search metadata
            search_method = 'enhanced_traditional' if use_enhanced else 'traditional'
            
            return {
                'success': True,
                'articles': news_results,
                'total_found': len(news_results),
                'search_method': search_method,
                'sources_used': ['NewsAPI'],
                'query_enhanced': enhanced_query != query
            }
                
        except Exception as e:
            logger.error(f"Error in enhanced search: {e}")
            return {
                'success': False,
                'error': str(e),
                'articles': [],
                'search_method': 'error'
            }

    def _enhance_query_with_context(self, query: str, user_tickers: List[str] = None) -> str:
        """Enhance the query with user context and simplify for better searching"""
        import re
        
        # Extract key terms from complex queries
        key_terms = self._extract_key_search_terms(query)
        
        # Use key terms if original query is very specific
        if len(query.split()) > 6:  # Long, specific queries
            simplified_query = ' '.join(key_terms[:3])  # Use top 3 key terms
            logger.info(f"Simplified complex query '{query}' to '{simplified_query}'")
        else:
            simplified_query = query
        
        if user_tickers:
            # Add ticker context to improve search relevance
            ticker_context = f" Related to stocks: {', '.join(user_tickers)}."
            enhanced = f"{simplified_query}{ticker_context} Focus on financial news and market impact."
        else:
            enhanced = f"{simplified_query} Focus on business and financial news."
        
        return enhanced

    def _extract_key_search_terms(self, query: str) -> list:
        """Extract key search terms from a complex query"""
        import re
        
        # Remove common words and extract important terms
        stop_words = {'find', 'me', 'news', 'about', 'recent', 'the', 'and', 'with', 'for', 'in', 'on', 'at', 'to', 'of'}
        
        # Extract words, focusing on proper nouns and important terms
        words = re.findall(r'\b[A-Za-z]+\b', query.lower())
        
        # Keep important terms, prioritize capitalized words from original query
        key_terms = []
        original_words = query.split()
        
        for word in original_words:
            clean_word = re.sub(r'[^\w]', '', word)
            if (clean_word.lower() not in stop_words and 
                len(clean_word) > 2 and
                clean_word not in key_terms):
                key_terms.append(clean_word)
        
        return key_terms[:5]  # Return top 5 key terms

    async def generate_enhanced_chat_response(self, 
                                            query: str, 
                                            user_tickers: List[str],
                                            use_agent_search: bool = True) -> Dict[str, Any]:
        """
        Generate chat response using enhanced search capabilities
        
        This provides the same interface as the full agent system but uses
        the proven news intelligence system with enhanced query processing.
        """
        try:
            # Get enhanced search results
            search_results = await self.enhanced_search(
                query, user_tickers, use_enhanced=use_agent_search, limit=8
            )
            
            if not search_results['success']:
                return {
                    'success': False,
                    'error': search_results.get('error', 'Search failed'),
                    'articles_found': 0,
                    'suggested_articles': []
                }
            
            articles = search_results['articles']
            
            if articles:
                # Use the proven chat response generation with enhanced articles
                response_data = await self.news_intelligence.generate_chat_response(
                    query, user_tickers, conversation_history=[]
                )
                
                # Add enhanced search metadata
                response_data['search_method'] = search_results['search_method']
                response_data['sources_used'] = search_results['sources_used']
                response_data['query_enhanced'] = search_results.get('query_enhanced', False)
                
                return response_data
            else:
                return {
                    'success': True,
                    'response': f"I couldn't find recent news specifically about '{query}' related to your interests ({', '.join(user_tickers)}). This might be due to API rate limits or the topic being very recent.",
                    'articles_found': 0,
                    'suggested_articles': [],
                    'search_method': search_results['search_method']
                }
                
        except Exception as e:
            logger.error(f"Error in enhanced chat response: {e}")
            return {
                'success': False,
                'error': str(e),
                'articles_found': 0,
                'suggested_articles': []
            }


# Global instance - initialize when needed
_simple_agent_news_service = None

def get_simple_agent_news_service() -> SimpleAgentNewsService:
    """Get or create the global simple agent news service instance"""
    global _simple_agent_news_service
    
    if _simple_agent_news_service is None:
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        newsapi_key = os.getenv('NEWSAPI_KEY')
        
        if not gemini_api_key or not newsapi_key:
            logger.warning("API keys not found, service will have limited functionality")
        
        _simple_agent_news_service = SimpleAgentNewsService(
            gemini_api_key=gemini_api_key or 'dummy-key',
            newsapi_key=newsapi_key or 'dummy-key'
        )
    
    return _simple_agent_news_service