"""
Consolidated News Intelligence Module

Combines smart filtering and AI personalization into a single cohesive module.
This module handles:
- NewsAPI integration with smart query strategies  
- Gemini AI-powered content analysis and relevance scoring
- Source credibility evaluation
- Article filtering and personalization
"""

import asyncio
import yfinance as yf
import google.generativeai as genai
import json
import os
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from prompts import AgentPrompts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@dataclass
class SourceCredibility:
    name: str
    credibility_score: float  # 0.0 to 1.0
    category: str  # "tier1", "tier2", "tier3", "blog", "spam"
    reasoning: str

@dataclass
class ArticleRelevance:
    article_id: str
    relevance_score: float  # 0.0 to 1.0
    reasoning: str
    key_topics: List[str]
    investment_impact: str  # "high", "medium", "low", "none"
    content_quality: str   # "excellent", "good", "poor", "spam"
    should_include: bool

class NewsIntelligenceService:
    """Unified service for intelligent news filtering and personalization"""
    
    def __init__(self):
        # Initialize Gemini AI
        self.gemini_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 2048,
            }
        )
        
        # Initialize NewsAPI
        self.newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))
        
        # High-quality financial news sources
        self.quality_sources = [
            'reuters', 'bloomberg', 'wsj', 'financial-times', 'marketwatch', 
            'cnbc', 'associated-press', 'bbc-news', 'cnn', 'fortune'
        ]
        
        # Cache for source credibility to avoid repeated API calls
        self.source_cache = {}
        
    async def get_personalized_news(self, user_tickers: List[str], user_preferences: dict, limit: int = 20) -> List[dict]:
        """Main entry point: Get personalized news using intelligent filtering"""
        
        logger.info(f"🔍 Getting personalized news for tickers: {user_tickers}")
        
        try:
            # Step 1: Fetch quality financial news
            raw_articles = await self._fetch_quality_news(user_tickers)
            logger.info(f"📰 Fetched {len(raw_articles)} raw articles")
            
            # Step 2: Pre-filter obvious junk
            pre_filtered = self._pre_filter_articles(raw_articles, user_tickers)
            
            if not pre_filtered:
                logger.warning("⚠️ No articles passed pre-filtering")
                return []
            
            # Step 3: AI analysis and scoring
            logger.info(f"🤖 Analyzing {len(pre_filtered)} articles with Gemini AI")
            analyzed_articles = await self._analyze_articles_with_ai(pre_filtered, user_tickers, user_preferences)
            
            # Step 4: Final filtering and sorting
            relevant_articles = [
                article for article in analyzed_articles 
                if article.get('include_in_feed', False) and article.get('relevance_score', 0) > 0.4
            ]
            
            relevant_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            logger.info(f"✅ Found {len(relevant_articles)} relevant articles")
            return relevant_articles[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error in get_personalized_news: {e}")
            return []
    
    async def _fetch_quality_news(self, user_tickers: List[str]) -> List[dict]:
        """Fetch news using advanced query strategies"""
        
        all_articles = []
        
        # Strategy 1: Company-specific financial news
        for ticker in user_tickers[:3]:  # Limit to avoid rate limits
            try:
                logger.info(f"📊 Fetching news for {ticker}")
                
                # Get company info for better search
                company_info = await self._get_company_info(ticker)
                company_name = company_info.get('name', ticker)
                
                # Advanced financial queries
                financial_queries = [
                    f'"{company_name}"',
                    f'"{ticker}"',
                    f'"{company_name}" AND (earnings OR revenue OR profit OR quarterly)',
                    f'"{ticker}" AND (stock OR shares OR price OR trading)',
                    f'"{ticker}" AND (analyst OR rating OR target OR recommendation)'
                ]
                
                for query in financial_queries:
                    try:
                        response = self.newsapi.get_everything(
                            q=query,
                            language="en",
                            sort_by="publishedAt",
                            page_size=10
                        )
                        
                        articles = response.get('articles', [])
                        all_articles.extend(articles)
                        await asyncio.sleep(0.5)  # Rate limiting
                        
                    except Exception as e:
                        logger.warning(f"Query '{query[:30]}...' failed: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error fetching news for {ticker}: {e}")
                continue
        
        # Strategy 2: General market context
        try:
            logger.info("📈 Fetching market context news")
            market_queries = [
                'stock market AND (federal reserve OR inflation OR interest rates)',
                'earnings season AND (guidance OR results)',
                'market AND (volatility OR correction OR rally)'
            ]
            
            for query in market_queries:
                try:
                    response = self.newsapi.get_everything(
                        q=query,
                        language='en',
                        sort_by='publishedAt',
                        page_size=5,
                        sources=','.join(self.quality_sources[:5]),
                        from_param=(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
                    )
                    
                    articles = response.get('articles', [])
                    all_articles.extend(articles)
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Market query failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching market news: {e}")
        
        # Remove duplicates
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        logger.info(f"📋 Collected {len(unique_articles)} unique articles")
        return unique_articles
    
    def _pre_filter_articles(self, articles: List[dict], user_tickers: List[str]) -> List[dict]:
        """Quick pre-filtering to remove obvious junk"""
        
        filtered_articles = []
        ticker_keywords = user_tickers + [ticker.lower() for ticker in user_tickers]
        
        for article in articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            
            # Skip if no title or description
            if not title or not description:
                continue
                
            # Skip obvious spam indicators
            spam_indicators = [
                'buy now', 'limited time', 'exclusive offer', 'sign up today',
                'click here', 'free trial', 'act now', '100% guaranteed'
            ]
            
            if any(spam in title or spam in description for spam in spam_indicators):
                continue
            
            # Must have financial relevance
            financial_keywords = [
                'stock', 'shares', 'market', 'trading', 'investor', 'price',
                'earnings', 'revenue', 'profit', 'financial', 'economy',
                'analyst', 'rating', 'target', 'sec', 'ipo', 'merger'
            ] + ticker_keywords
            
            has_financial_content = any(
                keyword in title or keyword in description 
                for keyword in financial_keywords
            )
            
            if has_financial_content:
                filtered_articles.append(article)
        
        logger.info(f"Pre-filtered from {len(articles)} to {len(filtered_articles)} articles")
        return filtered_articles
    
    async def _analyze_articles_with_ai(self, articles: List[dict], user_tickers: List[str], user_preferences: dict) -> List[dict]:
        """Analyze articles using Gemini AI for relevance and quality scoring"""
        
        analyzed_articles = []
        batch_size = 5  # Process in smaller batches to avoid rate limits
        
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
            try:
                batch_results = await self._analyze_article_batch(batch, user_tickers, user_preferences)
                analyzed_articles.extend(batch_results)
                
                # Rate limiting between batches
                if i + batch_size < len(articles):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error analyzing batch {i//batch_size + 1}: {e}")
                # Add articles without analysis rather than losing them
                for article in batch:
                    article['relevance_score'] = 0.3
                    article['include_in_feed'] = False
                analyzed_articles.extend(batch)
                continue
        
        return analyzed_articles
    
    async def _analyze_article_batch(self, articles: List[dict], user_tickers: List[str], user_preferences: dict) -> List[dict]:
        """Analyze a batch of articles with Gemini AI"""
        
        # Prepare articles for analysis
        articles_text = []
        for i, article in enumerate(articles):
            article_text = f"""
            Article {i+1}:
            Title: {article.get('title', 'No title')}
            Description: {article.get('description', 'No description')}
            Source: {article.get('source', {}).get('name', 'Unknown source')}
            """
            articles_text.append(article_text)
        
        analysis_prompt = f"""
        You are a financial news analyst. Analyze these articles for relevance to a user with these characteristics:
        
        User Profile:
        - Stock tickers of interest: {user_tickers}
        - Investment style: {user_preferences.get('investment_style', 'balanced')}
        - Experience level: {user_preferences.get('experience_level', 'intermediate')}
        
        Articles to analyze:
        {"".join(articles_text)}
        
        For each article, provide a JSON object with:
        {{
            "article_index": number (1-{len(articles)}),
            "relevance_score": float (0.0-1.0),
            "is_financial_news": boolean,
            "source_credible": boolean,
            "include_in_feed": boolean,
            "reasoning": "brief explanation",
            "key_topics": ["topic1", "topic2"],
            "investment_impact": "high|medium|low|none"
        }}
        
        Scoring guidelines:
        - 0.9-1.0: Directly about user's tickers with significant financial impact
        - 0.7-0.8: Related to user's tickers or sector with moderate impact  
        - 0.5-0.6: General financial news relevant to user's investment style
        - 0.3-0.4: Tangentially related financial news
        - 0.0-0.2: Not relevant or low quality
        
        Return only a JSON array of analysis objects, no other text.
        """
        
        try:
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                analysis_prompt
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            analyses = json.loads(response_text)
            
            # Apply analysis to articles
            for analysis in analyses:
                article_idx = analysis['article_index'] - 1
                if 0 <= article_idx < len(articles):
                    articles[article_idx].update({
                        'relevance_score': analysis['relevance_score'],
                        'include_in_feed': analysis['include_in_feed'],
                        'gemini_analysis': analysis
                    })
                    
                    # Log included articles
                    if analysis['include_in_feed']:
                        title = articles[article_idx].get('title', 'No title')
                        score = analysis['relevance_score']
                        logger.info(f"✅ Included: {title[:60]}... (Score: {score:.2f})")
            
            return articles
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            # Fallback scoring
            for article in articles:
                article['relevance_score'] = 0.3
                article['include_in_feed'] = False
            return articles
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            # Fallback scoring
            for article in articles:
                article['relevance_score'] = 0.3
                article['include_in_feed'] = False
            return articles
    
    async def _get_company_info(self, ticker: str) -> dict:
        """Get company information for better search queries"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'name': info.get('longName', ticker),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'description': info.get('businessSummary', '')[:200] if info.get('businessSummary') else ''
            }
        except Exception as e:
            logger.warning(f"Could not get company info for {ticker}: {e}")
            return {'name': ticker}
    
    async def search_news_by_topic(self, topic: str, user_tickers: List[str], limit: int = 10) -> List[dict]:
        """Search for news by specific topic with user context"""
        
        logger.info(f"🔍 Searching news for topic: {topic}")
        
        # Enhance topic with user context
        ticker_context = f" AND ({' OR '.join(user_tickers)})" if user_tickers else ""
        enhanced_query = f"{topic}{ticker_context}"
        
        try:
            response = self.newsapi.get_everything(
                q=enhanced_query,
                language="en",
                sort_by="publishedAt",
                page_size=limit * 2
            )
            
            articles = response.get('articles', [])
            
            # Quick analysis for search results
            pre_filtered = self._pre_filter_articles(articles, user_tickers)
            
            if pre_filtered:
                analyzed = await self._analyze_articles_with_ai(
                    pre_filtered, user_tickers, 
                    {'investment_style': 'balanced', 'experience_level': 'intermediate'}
                )
                
                relevant = [a for a in analyzed if a.get('include_in_feed', False)]
                relevant.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                
                return relevant[:limit]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error searching news by topic {topic}: {e}")
            return []
    
    async def generate_chat_response(self, query: str, user_tickers: List[str], 
                                   conversation_history: List[dict] = None) -> dict:
        """Generate conversational response with actual news articles"""
        
        # First, search for relevant articles
        relevant_articles = await self.search_news_by_topic(query, user_tickers, limit=8)
        
        # Prepare context for chat response
        if relevant_articles:
            articles_context = []
            for article in relevant_articles[:5]:
                context = f"""
                - {article['title']}
                  Source: {article.get('source', {}).get('name', 'Unknown')}
                  Summary: {article.get('description', 'No summary')[:100]}...
                  Relevance: {article.get('relevance_score', 0):.1f}/1.0
                """
                articles_context.append(context)
            
            # Create the user query context
            user_query_context = f"""
            User Question: "{query}"
            User's Stock Interests: {user_tickers}
            
            Relevant Recent Articles:
            {"".join(articles_context)}
            
            Please provide a comprehensive response that directly addresses their question using the articles above. Reference specific news sources and provide actionable insights based on current news. Keep the response informative but concise (2-3 paragraphs).
            """
            
            # Combine system prompt with user context
            full_prompt = f"{AgentPrompts.QUERY_AGENT_SYSTEM}\n\n{user_query_context}"
            
            try:
                response = await asyncio.to_thread(
                    self.gemini_model.generate_content,
                    full_prompt
                )
                
                return {
                    'success': True,
                    'response': response.text,
                    'articles_found': len(relevant_articles),
                    'suggested_articles': relevant_articles[:3]  # Top 3 for display
                }
                
            except Exception as e:
                logger.error(f"Error generating chat response: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'articles_found': len(relevant_articles),
                    'suggested_articles': relevant_articles[:3] if relevant_articles else []
                }
        else:
            return {
                'success': True,
                'response': f"I couldn't find recent news specifically about '{query}' related to your interests ({', '.join(user_tickers)}). This might be due to API rate limits or the topic being very recent. Try asking about specific companies or broader market trends.",
                'articles_found': 0,
                'suggested_articles': []
            }