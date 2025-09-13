"""
Agent Integration Service for News Platform

This service integrates the PlannerAgent and retriever system with the main
news platform, allowing users to get enhanced search results through the
personalized news interface.
"""

import logging
import asyncio
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Set up logger first
logger = logging.getLogger(__name__)

# Try to import agent modules with better error handling
AGENTS_AVAILABLE = False
EnhancedPlannerAgent = None
PlannerAgent = None

try:
    # Add the news_agent directory to the Python path
    news_agent_path = os.path.join(os.path.dirname(__file__), '..', 'news_agent')
    if news_agent_path not in sys.path:
        sys.path.insert(0, news_agent_path)
    
    # Try importing as direct modules first
    import agent
    PlannerAgent = agent.PlannerAgent
    logger.info("Successfully imported PlannerAgent")
    AGENTS_AVAILABLE = True
    
    try:
        # Try importing enhanced agent
        import integration.planner_aggregator as planner_agg
        EnhancedPlannerAgent = planner_agg.EnhancedPlannerAgent
        logger.info("Successfully imported EnhancedPlannerAgent")
    except ImportError as e:
        logger.warning(f"EnhancedPlannerAgent not available: {e}")
        logger.info("Will use basic PlannerAgent only")
        
except ImportError as e:
    logger.warning(f"Agent modules not available: {e}")
    logger.warning("Agent integration will be disabled. Using traditional news intelligence only.")
    AGENTS_AVAILABLE = False

from news_intelligence import NewsIntelligenceService


class AgentNewsService:
    """
    Service that integrates the PlannerAgent with news intelligence
    for enhanced search and personalization capabilities.
    """
    
    def __init__(self, 
                 gemini_api_key: str,
                 newsapi_key: str,
                 enable_enhanced_agent: bool = True,
                 max_concurrent_retrievers: int = 3):
        """
        Initialize the Agent News Service
        
        Args:
            gemini_api_key: API key for Gemini AI
            newsapi_key: API key for NewsAPI
            enable_enhanced_agent: Whether to use EnhancedPlannerAgent with aggregation
            max_concurrent_retrievers: Max concurrent retrievers to use
        """
        self.gemini_api_key = gemini_api_key
        self.newsapi_key = newsapi_key
        self.enable_enhanced_agent = enable_enhanced_agent
        
        # Initialize the news intelligence service (existing)
        self.news_intelligence = NewsIntelligenceService(gemini_api_key, newsapi_key)
        
        # Initialize the agent system
        self.agent = None
        self._initialize_agent(max_concurrent_retrievers)
        
    def _initialize_agent(self, max_concurrent_retrievers: int):
        """Initialize the appropriate agent based on configuration"""
        if not AGENTS_AVAILABLE:
            logger.warning("Agent modules not available - agent integration disabled")
            self.agent = None
            self.enable_enhanced_agent = False
            return
            
        try:
            if self.enable_enhanced_agent and EnhancedPlannerAgent:
                # Try to initialize EnhancedPlannerAgent with aggregation
                self.agent = EnhancedPlannerAgent(
                    max_concurrent_retrievers=max_concurrent_retrievers,
                    gemini_api_key=self.gemini_api_key,
                    enable_aggregation=True  # This may fall back if Supabase not configured
                )
                logger.info("Initialized EnhancedPlannerAgent")
            elif PlannerAgent:
                # Fall back to basic PlannerAgent
                self.agent = PlannerAgent(max_concurrent_retrievers)
                logger.info("Initialized basic PlannerAgent")
            else:
                logger.warning("No agent classes available")
                self.agent = None
                self.enable_enhanced_agent = False
                
        except Exception as e:
            logger.warning(f"Failed to initialize agent: {e}")
            logger.info("Agent integration disabled")
            self.agent = None
            self.enable_enhanced_agent = False

    async def enhanced_search(self, 
                            query: str, 
                            user_tickers: List[str] = None,
                            use_agent_search: bool = True,
                            limit: int = 10) -> Dict[str, Any]:
        """
        Enhanced search that combines agent retrieval with news intelligence
        
        Args:
            query: User's search query
            user_tickers: User's stock interests for personalization
            use_agent_search: Whether to use agent search or fall back to news intelligence
            limit: Maximum number of articles to return
            
        Returns:
            Dict containing search results and metadata
        """
        try:
            if use_agent_search and self.agent and AGENTS_AVAILABLE:
                # Use agent system for comprehensive search
                agent_results = await self._search_with_agent(query, user_tickers)
                
                # Combine with traditional news intelligence results
                news_results = await self.news_intelligence.search_news_by_topic(
                    query, user_tickers or [], limit=5
                )
                
                # Merge and deduplicate results
                combined_results = self._merge_results(agent_results, news_results)
                
                return {
                    'success': True,
                    'articles': combined_results[:limit],
                    'total_found': len(combined_results),
                    'search_method': 'agent_enhanced',
                    'agent_sources': agent_results.get('sources_used', []),
                    'traditional_sources': ['NewsAPI']
                }
            else:
                # Fall back to traditional news intelligence
                reason = 'agents_unavailable' if not AGENTS_AVAILABLE else 'traditional_requested'
                news_results = await self.news_intelligence.search_news_by_topic(
                    query, user_tickers or [], limit=limit
                )
                
                return {
                    'success': True,
                    'articles': news_results,
                    'total_found': len(news_results),
                    'search_method': f'traditional_{reason}',
                    'sources': ['NewsAPI']
                }
                
        except Exception as e:
            logger.error(f"Error in enhanced search: {e}")
            return {
                'success': False,
                'error': str(e),
                'articles': [],
                'search_method': 'error'
            }

    async def _search_with_agent(self, query: str, user_tickers: List[str] = None) -> Dict[str, Any]:
        """Use the agent system to search across multiple sources"""
        if not self.agent or not AGENTS_AVAILABLE:
            logger.warning("Agent not available for search")
            return {'articles': [], 'sources_used': [], 'error': 'Agent not available'}
            
        try:
            # Enhance query with user context
            enhanced_query = self._enhance_query_with_context(query, user_tickers)
            
            if hasattr(self.agent, 'run_async'):
                # Enhanced agent with aggregation
                agent_results = await self.agent.run_async(
                    enhanced_query,
                    user_preferences={'tickers': user_tickers or []},
                    return_aggregated=True
                )
            elif hasattr(self.agent, 'run'):
                # Basic agent
                agent_results = await self.agent.run(enhanced_query)
            else:
                logger.error("Agent has no run or run_async method")
                return {'articles': [], 'sources_used': [], 'error': 'Invalid agent'}
            
            # Convert agent results to news format
            formatted_articles = self._format_agent_results(agent_results)
            
            return {
                'articles': formatted_articles,
                'sources_used': self._extract_sources_used(agent_results),
                'raw_results': agent_results
            }
            
        except Exception as e:
            logger.error(f"Error in agent search: {e}")
            return {'articles': [], 'sources_used': [], 'error': str(e)}

    def _enhance_query_with_context(self, query: str, user_tickers: List[str] = None) -> str:
        """Enhance the query with user context for better agent searching"""
        if user_tickers:
            ticker_context = f" Related to stocks: {', '.join(user_tickers)}."
            enhanced = f"{query}{ticker_context} Focus on financial news and market impact."
        else:
            enhanced = f"{query} Focus on business and financial news."
        
        return enhanced

    def _format_agent_results(self, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert agent results to the news article format expected by the frontend"""
        formatted_articles = []
        
        try:
            # Handle different result formats from different agent types
            if isinstance(agent_results, dict):
                if 'aggregated_results' in agent_results:
                    # Enhanced agent with aggregation
                    results = agent_results['aggregated_results']
                elif 'results' in agent_results:
                    # Basic agent results
                    results = agent_results['results']
                else:
                    results = []
                    
                for item in results:
                    if isinstance(item, dict):
                        # Try to extract article information
                        article = self._extract_article_from_result(item)
                        if article:
                            formatted_articles.append(article)
            
        except Exception as e:
            logger.error(f"Error formatting agent results: {e}")
        
        return formatted_articles

    def _extract_article_from_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract article information from a single agent result"""
        try:
            # Handle different result structures
            title = result.get('title') or result.get('headline') or result.get('name', 'Untitled')
            description = result.get('description') or result.get('summary') or result.get('snippet', '')
            url = result.get('url') or result.get('link', '')
            source = result.get('source') or result.get('domain', 'Unknown')
            
            if not title or not url:
                return None
                
            return {
                'title': title,
                'description': description,
                'url': url,
                'source': {'name': source},
                'publishedAt': result.get('publishedAt') or datetime.now().isoformat(),
                'relevance_score': result.get('relevance_score', 0.5),
                'sentiment_score': result.get('sentiment_score', 0.0),
                'category': result.get('category', 'general'),
                'agent_source': True  # Flag to indicate this came from agent search
            }
            
        except Exception as e:
            logger.error(f"Error extracting article from result: {e}")
            return None

    def _extract_sources_used(self, agent_results: Dict[str, Any]) -> List[str]:
        """Extract the names of sources that were used in the agent search"""
        sources = []
        try:
            if isinstance(agent_results, dict):
                if 'retriever_results' in agent_results:
                    for retriever_name, _ in agent_results['retriever_results'].items():
                        sources.append(retriever_name)
                elif 'sources' in agent_results:
                    sources = agent_results['sources']
        except Exception as e:
            logger.error(f"Error extracting sources: {e}")
        
        return sources

    def _merge_results(self, agent_results: Dict[str, Any], news_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge agent results with traditional news results, removing duplicates"""
        merged = []
        seen_urls = set()
        
        # Add agent results first (they might have better variety)
        for article in agent_results.get('articles', []):
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(article)
        
        # Add news intelligence results
        for article in news_results:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                # Mark as traditional source
                article['agent_source'] = False
                merged.append(article)
        
        # Sort by relevance score if available
        merged.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return merged

    async def generate_enhanced_chat_response(self, 
                                            query: str, 
                                            user_tickers: List[str],
                                            use_agent_search: bool = True) -> Dict[str, Any]:
        """
        Generate chat response using enhanced search capabilities
        
        This replaces the traditional generate_chat_response with agent-powered search
        """
        try:
            # Get enhanced search results
            search_results = await self.enhanced_search(
                query, user_tickers, use_agent_search=use_agent_search, limit=8
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
                # Use traditional chat response generation with enhanced articles
                response_data = await self.news_intelligence.generate_chat_response(
                    query, user_tickers, conversation_history=[]
                )
                
                # Override the suggested articles with our enhanced results
                response_data['suggested_articles'] = articles[:3]
                response_data['articles_found'] = len(articles)
                response_data['search_method'] = search_results['search_method']
                response_data['sources_used'] = search_results.get('agent_sources', [])
                
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
_agent_news_service = None

def get_agent_news_service() -> AgentNewsService:
    """Get or create the global agent news service instance"""
    global _agent_news_service
    
    if _agent_news_service is None:
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        newsapi_key = os.getenv('NEWSAPI_KEY')
        
        if not gemini_api_key or not newsapi_key:
            logger.warning("API keys not found, agent service will have limited functionality")
        
        _agent_news_service = AgentNewsService(
            gemini_api_key=gemini_api_key or 'dummy-key',
            newsapi_key=newsapi_key or 'dummy-key',
            enable_enhanced_agent=bool(gemini_api_key),  # Only enable if we have the key
            max_concurrent_retrievers=3
        )
    
    return _agent_news_service