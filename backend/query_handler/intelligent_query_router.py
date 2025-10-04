"""
Intelligent Query Router - Routes user queries to appropriate data sources
Handles database lookups, topic matching, and fallback to new searches
"""

import logging
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import requests

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Import research DB manager
try:
    from deep_news_agent.db.research_db_manager import ResearchDBManager
    from deep_news_agent.agents.orchestrator_agent import OrchestratorAgent
    from deep_news_agent.agents.interfaces import CompanyContext
    DEEP_NEWS_AVAILABLE = True
except Exception as e:
    DEEP_NEWS_AVAILABLE = False
    print(f"Warning: deep_news_agent not available: {e}")

# Try to import analyzers (support both OpenAI and Gemini)
try:
    from .hybrid_query_analyzer_openai import HybridQueryAnalyzer as OpenAIQueryAnalyzer
    from .hybrid_query_analyzer_openai import QueryIntent
    OPENAI_ANALYZER_AVAILABLE = True
except Exception as e:
    OPENAI_ANALYZER_AVAILABLE = False

try:
    from .hybrid_query_analyzer import HybridQueryAnalyzer as GeminiQueryAnalyzer
    if not OPENAI_ANALYZER_AVAILABLE:
        from .hybrid_query_analyzer import QueryIntent
    GEMINI_ANALYZER_AVAILABLE = True
except Exception as e:
    GEMINI_ANALYZER_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_ticker(company_name: str) -> Optional[str]:
    """
    Get ticker symbol from company name using Yahoo Finance API
    Returns ticker symbol or None if not found
    """
    try:
        yfinance_url = "https://query2.finance.yahoo.com/v1/finance/search"
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        params = {"q": company_name, "quotes_count": 1, "country": "United States"}

        res = requests.get(url=yfinance_url, params=params, headers={'User-Agent': user_agent}, timeout=3)
        data = res.json()

        if data.get('quotes') and len(data['quotes']) > 0:
            ticker = data['quotes'][0]['symbol']
            logger.info(f"Resolved company name '{company_name}' to ticker '{ticker}'")
            return ticker

        logger.warning(f"No ticker found for company name '{company_name}'")
        return None

    except Exception as e:
        logger.error(f"Error getting ticker for '{company_name}': {e}")
        return None


class TopicMatcher:
    """
    Handles topic embedding generation and similarity matching
    Addresses the issue of topics not having embeddings yet
    """

    def __init__(self):
        """Initialize embedding model"""
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_cache = {}  # Cache for topic embeddings
        logger.info("TopicMatcher initialized with sentence-transformers model")

    def generate_topic_embedding(self, topic_name: str, topic_description: str = "") -> np.ndarray:
        """
        Generate embedding for a topic
        Combines topic name and description for richer representation
        """
        # Create composite text
        composite_text = f"{topic_name}"
        if topic_description:
            composite_text += f" {topic_description}"

        # Check cache
        cache_key = composite_text.lower()
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]

        # Generate embedding
        embedding = self.model.encode(composite_text, convert_to_numpy=True)

        # Cache it
        self.embedding_cache[cache_key] = embedding

        return embedding

    def match_query_to_topics(
        self,
        query_topics: List[str],
        existing_topics: List[Dict[str, Any]],
        threshold: float = 0.75
    ) -> Optional[Dict[str, Any]]:
        """
        Match extracted query topics to existing database topics using embeddings

        Args:
            query_topics: Topics extracted from user query
            existing_topics: Topics from database (each with 'name', 'description', etc.)
            threshold: Minimum similarity threshold (0.0-1.0)

        Returns:
            Best matching topic dict or None if no good match
        """
        if not query_topics or not existing_topics:
            return None

        # Combine query topics into single search phrase
        query_text = " ".join(query_topics)
        query_embedding = self.model.encode(query_text, convert_to_numpy=True)

        best_match = None
        best_score = 0.0

        for topic in existing_topics:
            # Generate embedding for this topic
            topic_name = topic.get('name', '')
            topic_desc = topic.get('description', '')

            topic_embedding = self.generate_topic_embedding(topic_name, topic_desc)

            # Calculate cosine similarity
            similarity = cosine_similarity(
                query_embedding.reshape(1, -1),
                topic_embedding.reshape(1, -1)
            )[0][0]

            logger.debug(f"Topic '{topic_name}' similarity: {similarity:.3f}")

            if similarity > best_score:
                best_score = similarity
                best_match = topic

        # Return match if above threshold
        if best_score >= threshold:
            logger.info(f"Found matching topic: '{best_match['name']}' (similarity: {best_score:.3f})")
            return {**best_match, 'similarity_score': best_score}

        logger.info(f"No topic match above threshold {threshold} (best: {best_score:.3f})")
        return None


class IntelligentQueryRouter:
    """
    Main router that coordinates query analysis, database lookups, and fallback searches
    Supports both OpenAI and Gemini for LLM operations
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        use_openai: bool = True  # Default to OpenAI if available
    ):
        """
        Initialize the router with necessary API keys

        Args:
            openai_api_key: OpenAI API key (preferred)
            gemini_api_key: Gemini API key (fallback)
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            use_openai: If True, prefer OpenAI over Gemini when both are available
        """
        # Initialize query analyzer based on available APIs
        self.analyzer = None
        self.analyzer_type = None

        if use_openai and openai_api_key and OPENAI_ANALYZER_AVAILABLE:
            self.analyzer = OpenAIQueryAnalyzer(openai_api_key)
            self.analyzer_type = "OpenAI"
            logger.info("✅ Using OpenAI query analyzer")
        elif gemini_api_key and GEMINI_ANALYZER_AVAILABLE:
            self.analyzer = GeminiQueryAnalyzer(gemini_api_key)
            self.analyzer_type = "Gemini"
            logger.info("✅ Using Gemini query analyzer")
        elif openai_api_key and OPENAI_ANALYZER_AVAILABLE:
            # Fallback to OpenAI if Gemini was preferred but not available
            self.analyzer = OpenAIQueryAnalyzer(openai_api_key)
            self.analyzer_type = "OpenAI"
            logger.info("✅ Using OpenAI query analyzer (fallback)")
        else:
            logger.error("❌ No query analyzer available! Need either OpenAI or Gemini API key")
            raise ValueError("No LLM API key provided or analyzers not available")

        # Initialize topic matcher
        self.topic_matcher = TopicMatcher()

        # Initialize research database manager
        self.research_db = None
        if supabase_url and supabase_key and DEEP_NEWS_AVAILABLE:
            try:
                self.research_db = ResearchDBManager(supabase_url, supabase_key)
                logger.info("✅ Research database manager initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize research DB: {e}")
                self.research_db = None
        else:
            logger.warning("⚠️ Research database not available")

        logger.info(f"IntelligentQueryRouter initialized with {self.analyzer_type} analyzer")

    def route_query(self, user_query: str) -> Dict[str, Any]:
        """
        Main entry point: Route a user query to appropriate data source

        Returns:
            {
                'source': 'cache' | 'fresh_search' | 'fallback',
                'articles': [...],
                'matched_topic': {...} or None,
                'query_intent': {...},
                'confidence': float
            }
        """
        logger.info(f"Routing query: '{user_query}'")

        # ===== STEP 1: Analyze Query =====
        query_intent = self.analyzer.analyze_query(user_query)

        logger.info(f"Query analysis complete: companies={query_intent.companies}, "
                   f"topics={query_intent.topics}, confidence={query_intent.confidence:.2f}")

        # ===== STEP 2: Determine Company =====
        company = self._determine_company(query_intent)

        if not company:
            logger.info("No company identified, returning fallback")
            return {
                'source': 'fallback',
                'articles': [],
                'matched_topic': None,
                'query_intent': query_intent.to_dict(),
                'confidence': query_intent.confidence,
                'message': 'No company identified in query'
            }

        logger.info(f"Target company: {company}")

        # ===== STEP 3: Check Database for Existing Topics (Company-Specific) =====
        if self.research_db:
            # IMPORTANT: Only get topics for THIS specific company
            company_topics = self._get_company_topics(company)

            if company_topics:
                logger.info(f"Found {len(company_topics)} existing topics for {company}")
                logger.debug(f"Company topics: {[t.get('name') for t in company_topics[:5]]}")

                # ===== STEP 4: Match Query to Company's Topics Only =====
                # Use topics if available, otherwise use keywords for matching
                search_terms = query_intent.topics if query_intent.topics else query_intent.keywords

                if search_terms:
                    # Only match against topics that belong to the extracted company
                    # This ensures "Tesla earnings" won't match "MSFT earnings"
                    matched_topic = self.topic_matcher.match_query_to_topics(
                        query_topics=search_terms,
                        existing_topics=company_topics,  # Already filtered by company
                        threshold=0.30  # Lower threshold for broader matching
                    )

                    if matched_topic:
                        # ✅ CACHE HIT - Return cached articles for THIS company
                        logger.info(f"✅ Cache hit! Company: {company}, Topic: {matched_topic['name']}")
                        articles = self._get_topic_articles(matched_topic)

                        return {
                            'source': 'cache',
                            'articles': articles,
                            'matched_topic': matched_topic,
                            'matched_company': company,  # Include company for verification
                            'query_intent': query_intent.to_dict(),
                            'confidence': matched_topic['similarity_score'],
                            'message': f"Found cached research on {company}: {matched_topic['name']}"
                        }
                else:
                    logger.info("No search terms (topics or keywords) to match against")

        # ===== STEP 5: No Match - Trigger Fresh Search =====
        logger.info("❌ No matching topic found, triggering fresh search")
        return self._trigger_fresh_search(company, query_intent)

    def _determine_company(self, query_intent: QueryIntent) -> Optional[str]:
        """
        Determine target company ticker from query intent
        Database stores companies by TICKER in the 'name' field (e.g., 'AAPL', 'TSLA')
        Uses Yahoo Finance API to convert company names to tickers
        """
        # Prefer ticker if available (but filter out common false positives)
        false_positive_tickers = {'AI', 'IT', 'US', 'UK', 'EU', 'CEO', 'CFO', 'CTO', 'IPO'}
        if query_intent.tickers:
            ticker = query_intent.tickers[0].upper()
            if ticker not in false_positive_tickers:
                logger.info(f"Using extracted ticker: {ticker}")
                return ticker

        # Fall back to company name and convert to ticker using Yahoo Finance
        if query_intent.companies:
            company = query_intent.companies[0]

            # Clean up common issues with spaCy extraction
            # "Apple Vision" → "Apple"
            known_companies = ['Apple', 'Microsoft', 'Google', 'Amazon', 'Tesla', 'Meta', 'Nvidia', 'Netflix', 'IBM']
            for known in known_companies:
                if company.startswith(known):
                    company = known
                    break

            # Use Yahoo Finance API to get ticker from company name
            ticker = get_ticker(company)
            if ticker:
                return ticker

            # If API fails and it's already ticker-like format, return as-is
            if len(company) <= 5 and company.isupper():
                logger.info(f"Using company as ticker: {company}")
                return company

        return None

    def _get_company_topics(self, company_ticker: str) -> List[Dict[str, Any]]:
        """
        Get existing topics for a company from database
        Database stores tickers in the 'name' column (e.g., 'AAPL', 'TSLA')

        Args:
            company_ticker: Ticker symbol (e.g., 'AAPL')
        """
        if not self.research_db:
            return []

        try:
            # Query companies table by ticker (stored in 'name' field)
            company_result = self.research_db.supabase.table("companies").select("id, name").eq("name", company_ticker).execute()

            if not company_result.data:
                logger.info(f"Company ticker '{company_ticker}' not found in database")
                return []

            company_id = company_result.data[0]['id']
            logger.info(f"Found company ID {company_id} for ticker '{company_ticker}'")

            # Get topics for this company
            topics_result = self.research_db.supabase.table("topics").select("""
                id, name, description, business_impact, confidence, urgency,
                final_score, rank_position, subtopics, extraction_date
            """).eq("company_id", company_id).order("rank_position", desc=False).limit(50).execute()

            if topics_result.data:
                logger.info(f"Found {len(topics_result.data)} topics for {company_ticker}")

            return topics_result.data if topics_result.data else []

        except Exception as e:
            logger.error(f"Error getting company topics for {company_ticker}: {e}")
            return []

    def _get_topic_articles(self, topic: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get articles associated with a topic"""
        if not self.research_db:
            return []

        try:
            topic_id = topic.get('id')
            if not topic_id:
                return []

            article_data = self.research_db.get_topic_articles(topic_id)

            # Transform to frontend format
            articles = []
            for item in article_data:
                article = item.get('articles', {})
                if article:
                    articles.append({
                        'id': article.get('id'),
                        'title': article.get('title'),
                        'url': article.get('url'),
                        'source': article.get('source'),
                        'published_date': article.get('published_date'),
                        'relevance_score': article.get('relevance_score', 0.5),
                        'contribution_strength': item.get('contribution_strength', 0.5)
                    })

            return articles

        except Exception as e:
            logger.error(f"Error getting topic articles: {e}")
            return []

    def _trigger_fresh_search(self, company: str, query_intent: QueryIntent) -> Dict[str, Any]:
        """
        Trigger a fresh search using the research agent
        This is the fallback when no matching topics are found
        """
        logger.info(f"Triggering fresh search for {company}: {query_intent.topics}")

        # For now, return a structure indicating fresh search is needed
        # The actual search will be triggered by the endpoint handler
        return {
            'source': 'fresh_search',
            'articles': [],
            'matched_topic': None,
            'query_intent': query_intent.to_dict(),
            'confidence': query_intent.confidence,
            'message': f'No cached research found. New search needed for {company}',
            'search_params': {
                'company': company,
                'topics': query_intent.topics,
                'keywords': query_intent.keywords
            }
        }

    def get_company_articles_direct(self, company: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Direct lookup of company articles without topic matching
        Useful for general company queries
        """
        if not self.research_db:
            return []

        try:
            # Use Supabase to get articles for company
            result = self.research_db.supabase.table("articles").select(
                "id, title, url, content, source, published_date, relevance_score"
            ).join("article_topics", "id", "article_id").join(
                "topics", "article_topics.topic_id", "id"
            ).join("companies", "topics.company_id", "id").eq(
                "companies.name", company
            ).order("published_date", desc=True).limit(limit).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Error getting company articles: {e}")
            return []
