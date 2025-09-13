"""
Enhanced Multi-Stage News Discovery Pipeline

This implements a sophisticated 4-stage news discovery process:
1. Initial Retrieval: Enhanced Planner gets diverse content from multiple sources
2. Aggregation & Analysis: Content is clustered and key points are extracted
3. Focused Re-search: Key points become Tavily search queries for reputable sources
4. Final Curation: Results are organized and presented to the UI

Integration with existing FastAPI backend and frontend chat interface.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

# Import existing components
from news_agent.integration.planner_aggregator import create_enhanced_planner
from news_agent.retrievers.tavily.tavily_search import TavilyRetriever

logger = logging.getLogger(__name__)


class EnhancedNewsDiscoveryPipeline:
    """
    Multi-stage news discovery pipeline that transforms broad queries
    into highly curated news from reputable sources.
    """

    def __init__(self, gemini_api_key: str, tavily_api_key: str, max_retrievers: int = 5):
        """
        Initialize the enhanced news discovery pipeline.

        Args:
            gemini_api_key: API key for Gemini AI (aggregation & summarization)
            tavily_api_key: API key for Tavily search (final high-quality search)
            max_retrievers: Maximum concurrent retrievers for initial search
        """
        self.gemini_api_key = gemini_api_key
        self.tavily_api_key = tavily_api_key

        # Initialize enhanced planner with aggregation
        self.enhanced_planner = create_enhanced_planner(
            gemini_api_key=gemini_api_key,
            max_retrievers=max_retrievers,
            config_overrides={
                'clustering': {
                    'min_cluster_size': 2,
                    'similarity_threshold': 0.65
                },
                'summarization': {
                    'max_tokens': 150,
                    'temperature': 0.3
                }
            }
        )

        logger.info("Enhanced News Discovery Pipeline initialized")

    async def discover_news(self, query: str, user_preferences: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Complete multi-stage news discovery pipeline.

        Args:
            query: User's original query
            user_preferences: User preferences for personalization

        Returns:
            Dictionary containing all pipeline results and final curated news
        """
        pipeline_start = datetime.now()
        pipeline_results = {
            'original_query': query,
            'timestamp': pipeline_start.isoformat(),
            'stages': {},
            'final_articles': [],
            'processing_stats': {}
        }

        try:
            # Stage 1: Initial Broad Retrieval & Aggregation
            logger.info(f"🔍 Stage 1: Initial retrieval for query: '{query}'")
            stage1_start = datetime.now()

            initial_results = await self.enhanced_planner.run_async(
                query=query,
                user_preferences=user_preferences,
                return_aggregated=True
            )

            stage1_time = (datetime.now() - stage1_start).total_seconds()
            pipeline_results['stages']['stage1_retrieval'] = {
                'duration': stage1_time,
                'total_sources': initial_results.get('aggregation', {}).get('total_sources', 0),
                'clusters_found': len(initial_results.get('summaries', []))
            }

            # Stage 2: Key Point Extraction
            logger.info("🧠 Stage 2: Extracting key points from aggregated content")
            stage2_start = datetime.now()

            key_points = self._extract_key_points_from_aggregation(initial_results)

            stage2_time = (datetime.now() - stage2_start).total_seconds()
            pipeline_results['stages']['stage2_extraction'] = {
                'duration': stage2_time,
                'key_points_found': len(key_points)
            }

            # Stage 3: Focused Tavily Re-search
            logger.info("📰 Stage 3: Focused search using extracted key points")
            stage3_start = datetime.now()

            tavily_articles = await self._focused_tavily_search(key_points, user_preferences)

            stage3_time = (datetime.now() - stage3_start).total_seconds()
            pipeline_results['stages']['stage3_focused_search'] = {
                'duration': stage3_time,
                'search_queries': len(key_points),
                'articles_found': len(tavily_articles)
            }

            # Stage 4: Final Curation & Organization
            logger.info("✨ Stage 4: Final curation and organization")
            stage4_start = datetime.now()

            # If no Tavily articles (rate limited or failed), use fallback from initial retriever results
            if not tavily_articles and initial_results:
                logger.info("📰 No Tavily articles available, using fallback from initial retriever results")
                tavily_articles = self._create_fallback_articles_from_retriever_results(initial_results, key_points)

            final_curated_articles = self._curate_and_organize_articles(
                tavily_articles, key_points, user_preferences
            )

            stage4_time = (datetime.now() - stage4_start).total_seconds()
            pipeline_results['stages']['stage4_curation'] = {
                'duration': stage4_time,
                'final_articles': len(final_curated_articles),
                'used_fallback': len(tavily_articles) > 0 and not any('tavily_premium' in str(a.get('source_type', '')) for a in tavily_articles)
            }

            # Compile final results
            pipeline_results.update({
                'key_points': key_points,
                'final_articles': final_curated_articles,
                'raw_aggregation': initial_results.get('summaries', []),
                'processing_stats': {
                    'total_duration': (datetime.now() - pipeline_start).total_seconds(),
                    'success': True
                }
            })

            total_time = (datetime.now() - pipeline_start).total_seconds()
            logger.info(f"✅ Pipeline completed successfully in {total_time:.2f}s")
            logger.info(f"📊 Final result: {len(final_curated_articles)} curated articles")

            return pipeline_results

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            pipeline_results['processing_stats'] = {
                'total_duration': (datetime.now() - pipeline_start).total_seconds(),
                'success': False,
                'error': str(e)
            }
            return pipeline_results

    def _extract_key_points_from_aggregation(self, aggregated_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract key points from aggregated content or raw articles to use as focused search queries.

        Args:
            aggregated_results: Results from enhanced planner with aggregation

        Returns:
            List of key points with search queries and metadata
        """
        key_points = []
        summaries = aggregated_results.get('summaries', [])

        # First, try to extract from clustered summaries (preferred method)
        for i, cluster_summary in enumerate(summaries):
            # Extract main topic as a focused search query
            title = cluster_summary.get('title', '')
            summary_text = cluster_summary.get('summary', '')
            key_points_list = cluster_summary.get('key_points', [])
            metadata = cluster_summary.get('metadata', {})

            # Create focused search queries from cluster content
            if title and summary_text:
                # Main cluster topic query
                main_query = self._create_focused_query(title, metadata.get('ticker'))
                key_points.append({
                    'query': main_query,
                    'type': 'main_topic',
                    'cluster_id': i,
                    'priority': 1,
                    'ticker': metadata.get('ticker'),
                    'original_title': title
                })

                # Additional queries from key points
                for j, key_point in enumerate(key_points_list[:2]):  # Limit to top 2 key points
                    if len(key_point) > 10:  # Only substantial key points
                        key_point_query = self._create_focused_query(key_point, metadata.get('ticker'))
                        key_points.append({
                            'query': key_point_query,
                            'type': 'key_point',
                            'cluster_id': i,
                            'priority': 2,
                            'ticker': metadata.get('ticker'),
                            'original_key_point': key_point
                        })

        # If no clustered summaries available, extract from raw articles (fallback)
        if not key_points:
            logger.info("📝 No clustered summaries found, extracting key points from raw articles")
            key_points = self._extract_key_points_from_raw_articles(aggregated_results)

        # Sort by priority and limit total queries
        key_points = sorted(key_points, key=lambda x: (x['priority'], -x['cluster_id']))[:8]

        logger.info(f"📝 Extracted {len(key_points)} focused search queries")
        return key_points

    def _extract_key_points_from_raw_articles(self, aggregated_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract key points directly from raw articles when aggregation fails.

        Args:
            aggregated_results: Results from enhanced planner

        Returns:
            List of key points extracted from article titles and content
        """
        key_points = []

        # Check different categories of articles
        article_categories = ['financial_news', 'general_news', 'breaking_news', 'sec_filings']

        cluster_id = 0
        for category in article_categories:
            articles = aggregated_results.get(category, [])

            for i, article in enumerate(articles[:3]):  # Limit to top 3 articles per category
                if isinstance(article, dict):
                    # Extract title and create focused query
                    title = article.get('title', article.get('headline', ''))
                    url = article.get('url', article.get('href', ''))
                    content = article.get('content', article.get('body', article.get('summary', '')))

                    if title and len(title) > 15:
                        # Create focused query from article title
                        focused_query = self._create_focused_query(title)

                        key_points.append({
                            'query': focused_query,
                            'type': 'article_title',
                            'cluster_id': cluster_id,
                            'priority': 2 if category == 'financial_news' else 3,
                            'ticker': None,
                            'original_title': title,
                            'source_url': url,
                            'source_category': category
                        })

                        cluster_id += 1

                    # Also try to extract key phrases from content if available
                    if content and len(content) > 50:
                        key_phrases = self._extract_key_phrases_from_content(content, title)

                        for phrase in key_phrases[:1]:  # Limit to 1 key phrase per article
                            if len(phrase) > 10:
                                phrase_query = self._create_focused_query(phrase)
                                key_points.append({
                                    'query': phrase_query,
                                    'type': 'content_phrase',
                                    'cluster_id': cluster_id,
                                    'priority': 3,
                                    'ticker': None,
                                    'original_phrase': phrase,
                                    'source_category': category
                                })
                                cluster_id += 1

        return key_points

    def _extract_key_phrases_from_content(self, content: str, title: str) -> List[str]:
        """
        Extract key phrases from article content for focused searches.

        Args:
            content: Article content
            title: Article title for context

        Returns:
            List of key phrases
        """
        import re

        # Clean content
        cleaned_content = re.sub(r'[^\w\s]', ' ', content.lower())
        title_lower = title.lower()

        # Look for important financial/business terms and phrases
        important_patterns = [
            r'\b(earnings|revenue|profit|loss|growth|decline|increase|decrease)\s+\w+',
            r'\b(announced|reported|posted|reached|achieved|signed|agreed)\s+\w+\s+\w+',
            r'\b(government|federal|regulatory|administration|congress)\s+\w+',
            r'\b(partnership|deal|contract|agreement|merger|acquisition)\s+\w+',
            r'\b(ai|artificial intelligence|technology|innovation|chips?|semiconductors?)\s+\w+',
        ]

        key_phrases = []

        # Extract phrases using patterns
        for pattern in important_patterns:
            matches = re.findall(pattern, cleaned_content)
            for match in matches[:2]:  # Limit matches per pattern
                if len(match) > 10 and match not in key_phrases:
                    # Don't duplicate title content
                    if match.lower() not in title_lower:
                        key_phrases.append(match)

        # Also look for company names and specific terms in the first 200 characters
        first_part = cleaned_content[:200]
        company_patterns = [
            r'\b(nvidia|nvda|microsoft|apple|google|amazon|tesla|meta)\b',
            r'\b([A-Z][a-z]+\s+Inc\.?|[A-Z][a-z]+\s+Corp\.?|[A-Z][a-z]+\s+LLC)\b'
        ]

        for pattern in company_patterns:
            matches = re.findall(pattern, first_part, re.IGNORECASE)
            for match in matches[:1]:  # Limit company mentions
                if len(match) > 3 and match.lower() not in title_lower:
                    key_phrases.append(f"{match} news update")

        return key_phrases[:3]  # Return top 3 phrases

    def _create_focused_query(self, content: str, ticker: Optional[str] = None) -> str:
        """
        Create a focused news-specific search query from content and ticker.

        Args:
            content: Content to create query from
            ticker: Optional stock ticker to include

        Returns:
            Focused search query optimized for news discovery
        """
        # Clean up the content
        clean_content = content.replace('"', '').replace('\n', ' ').strip()

        # Remove common non-news words to focus on key terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        content_words = [word for word in clean_content.split() if word.lower() not in stop_words]

        # Keep only the most important terms (first 8 words max)
        key_terms = ' '.join(content_words[:8])

        # Create news-focused query with explicit news intent
        if ticker and ticker not in key_terms:
            return f"{ticker} {key_terms} financial news report"
        else:
            return f"{key_terms} business news financial report"

    async def _focused_tavily_search(self, key_points: List[Dict], user_preferences: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Perform focused Tavily searches using extracted key points.

        Args:
            key_points: List of key points with search queries
            user_preferences: User preferences for search customization

        Returns:
            List of articles from Tavily search
        """
        all_articles = []

        # Configure premium financial news domains only - most reputable sources
        premium_news_domains = [
            "reuters.com",           # Reuters - Top financial news
            "bloomberg.com",         # Bloomberg - Financial markets leader
            "wsj.com",              # Wall Street Journal - Premium business news
            "ft.com",               # Financial Times - Global financial news
            "cnbc.com",             # CNBC - Financial TV and web
            "marketwatch.com",      # MarketWatch - Financial markets
            "apnews.com",           # Associated Press - Reliable wire service
            "barrons.com",          # Barron's - Investment news
            "businesswire.com",     # Business Wire - Official press releases
            "prnewswire.com",       # PR Newswire - Official press releases
            "sec.gov",              # SEC - Official regulatory filings
            "investor.com"          # Investor's Business Daily
        ]

        # Perform searches concurrently
        search_tasks = []
        for key_point in key_points:
            task = self._single_tavily_search(
                key_point['query'],
                premium_news_domains,
                key_point
            )
            search_tasks.append(task)

        # Execute searches in batches to respect rate limits
        batch_size = 3
        for i in range(0, len(search_tasks), batch_size):
            batch = search_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Search failed: {result}")

            # Small delay between batches
            if i + batch_size < len(search_tasks):
                await asyncio.sleep(1)

        logger.info(f"🔍 Tavily search completed: {len(all_articles)} articles found")
        return all_articles

    async def _single_tavily_search(self, query: str, domains: List[str], key_point_meta: Dict) -> List[Dict[str, Any]]:
        """
        Perform a single Tavily search for high-quality news articles only.

        Args:
            query: Search query
            domains: List of premium news domains to search
            key_point_meta: Metadata from the key point

        Returns:
            List of high-quality articles from this search
        """
        try:
            # Create enhanced news-focused query
            enhanced_query = f"news article {query} financial reporting"

            # Create Tavily retriever with news focus
            tavily_retriever = TavilyRetriever(
                query=enhanced_query,
                topic="news",  # Specifically target news content
                query_domains=domains
            )

            # Search with higher result count to filter better
            search_results = tavily_retriever.search(max_results=8)

            # Enhanced quality filtering and title extraction
            high_quality_articles = []

            for article in search_results:
                # Extract and validate article information
                article_data = self._extract_and_validate_article(article, query, key_point_meta, domains)

                if article_data:  # Only include if it passes quality checks
                    high_quality_articles.append(article_data)

            logger.info(f"Quality filtered: {len(high_quality_articles)} articles from {len(search_results)} raw results for '{query[:50]}'")
            return high_quality_articles

        except Exception as e:
            logger.error(f"Single Tavily search failed for query '{query}': {e}")
            return []

    def _extract_and_validate_article(self, article: Dict, query: str, key_point_meta: Dict, allowed_domains: List[str]) -> Optional[Dict[str, Any]]:
        """
        Extract and validate article data with strict quality controls.

        Args:
            article: Raw article data from Tavily
            query: Original search query
            key_point_meta: Key point metadata
            allowed_domains: List of allowed domains

        Returns:
            Validated article data or None if quality checks fail
        """
        try:
            # Extract basic data
            url = article.get('href', '')
            content = article.get('body', '')

            # Validation 1: Must have URL and substantial content
            if not url or len(content) < 100:
                return None

            # Validation 2: Must be from allowed premium domains
            domain = self._extract_domain(url)
            if not any(allowed_domain in domain for allowed_domain in allowed_domains):
                logger.debug(f"Rejected article from non-premium domain: {domain}")
                return None

            # Validation 3: Extract proper article title
            title = self._extract_proper_article_title(content, url)
            if not title or len(title) < 10:
                logger.debug(f"Rejected article with poor title: {title}")
                return None

            # Validation 4: Content quality checks
            if not self._is_quality_news_content(content, title):
                logger.debug(f"Rejected article with poor content quality")
                return None

            # Validation 5: Must be news-related (not just corporate pages)
            if not self._is_news_article(content, url):
                logger.debug(f"Rejected non-news content: {url}")
                return None

            # Extract publication date if available
            pub_date = self._extract_publication_date(content, url)

            # Calculate relevance score based on content quality
            relevance_score = self._calculate_article_relevance(content, title, query, domain)

            return {
                'title': title,
                'url': url,
                'content': self._create_clean_preview(content),
                'source': self._get_source_display_name(domain),
                'search_query': query,
                'cluster_id': key_point_meta.get('cluster_id'),
                'priority': key_point_meta.get('priority', 3),
                'ticker': key_point_meta.get('ticker'),
                'relevance_score': relevance_score,
                'timestamp': pub_date or datetime.now().isoformat(),
                'source_type': 'tavily_premium',
                'domain': domain,
                'quality_validated': True
            }

        except Exception as e:
            logger.error(f"Article validation failed: {e}")
            return None

    def _extract_proper_article_title(self, content: str, url: str) -> Optional[str]:
        """Extract proper article title using multiple strategies optimized for news sites."""
        import re

        # Strategy 1: Clean the content first to remove common noise
        cleaned_content = self._clean_content_for_title_extraction(content)

        # Strategy 2: Look for title patterns in cleaned content
        title_patterns = [
            # Pattern for headline-style content (all caps words, proper nouns)
            r'^([A-Z][A-Za-z\s]{15,120}(?:Inc\.|Corp\.|Ltd\.|Co\.)?(?:\s+[A-Z][A-Za-z\s]{10,50})?)',
            # Pattern for news-style sentences with companies/proper nouns
            r'([A-Z][A-Za-z\s]*(?:Inc\.|Corp\.|Ltd\.).*?(?:says|reports|announces|posts|reaches|agrees)[^.!?]{10,80}[.!?]?)',
            # Pattern for financial news headlines
            r'([A-Z][A-Za-z\s]*(?:stock|shares|earnings|revenue|profit|loss|merger|deal)[^.!?]{10,100}[.!?]?)',
            # Generic substantial sentences starting with capital
            r'^([A-Z][^.!?]{25,150}[.!?])',
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, cleaned_content[:800])  # Search in first 800 chars
            for match in matches:
                clean_title = self._clean_title(match.strip())
                if self._is_valid_title(clean_title):
                    return clean_title

        # Strategy 3: Try to extract from URL path
        url_title = self._extract_title_from_url(url)
        if url_title:
            return url_title

        # Strategy 4: Look for any reasonable sentence in the content
        sentences = re.split(r'[.!?]+', cleaned_content[:1000])
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:
                clean_sentence = self._clean_title(sentence)
                if self._is_valid_title(clean_sentence) and not self._contains_noise_words(clean_sentence):
                    return clean_sentence

        return None

    def _clean_content_for_title_extraction(self, content: str) -> str:
        """Clean content to improve title extraction."""
        import re

        # Remove common website noise
        noise_patterns = [
            r'Provide news feedback.*?error',
            r'Send a tip to our reporters',
            r'Most Popular.*?Opinion',
            r'Read Next.*?Most Popular',
            r'Use Alt \+ Down Arrow.*?expand',
            r'Subscribe.*?(?:today|now)',
            r'Sign up.*?newsletter',
            r'Follow.*?Twitter',
            r'Copyright.*?rights reserved',
            r'Advertisement.*?continue',
            r'Read more.*?here',
            r'Click here.*?more',
            r'View.*?(?:gallery|photos)',
            r'\s*\*\s*', # Remove asterisks
            r'\s*#\s*', # Remove hashtags
        ]

        cleaned = content
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    def _extract_title_from_url(self, url: str) -> Optional[str]:
        """Extract meaningful title from URL path."""
        import re
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path

            if not path or path == '/':
                return None

            # Extract meaningful parts from URL
            path_parts = [part for part in path.split('/') if part and len(part) > 3]
            if not path_parts:
                return None

            # Take the last meaningful part (usually the article slug)
            article_slug = path_parts[-1]

            # Clean up the slug
            article_slug = re.sub(r'\.(html|htm|php|aspx)$', '', article_slug)
            article_slug = article_slug.replace('-', ' ').replace('_', ' ')

            # Remove common URL noise
            article_slug = re.sub(r'\b\d{8,}\b', '', article_slug)  # Remove long numbers
            article_slug = re.sub(r'\b[a-z0-9]{8,}\b', '', article_slug)  # Remove IDs

            # Clean up and format
            article_slug = re.sub(r'\s+', ' ', article_slug).strip()

            if len(article_slug) > 15 and len(article_slug) < 150:
                # Capitalize properly
                words = article_slug.split()
                title_words = []
                for word in words:
                    if len(word) > 2 and word.lower() not in ['and', 'or', 'but', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with']:
                        title_words.append(word.capitalize())
                    else:
                        title_words.append(word.lower())

                if title_words:
                    title_words[0] = title_words[0].capitalize()  # Always capitalize first word
                    return ' '.join(title_words)

        except Exception:
            pass

        return None

    def _contains_noise_words(self, text: str) -> bool:
        """Check if text contains too many noise/navigation words."""
        text_lower = text.lower()

        noise_indicators = [
            'provide news feedback', 'send a tip', 'most popular', 'read next',
            'subscribe', 'sign up', 'follow us', 'copyright', 'advertisement',
            'click here', 'read more', 'view gallery', 'download', 'login',
            'register', 'contact us', 'about us', 'privacy policy', 'terms'
        ]

        noise_count = sum(1 for indicator in noise_indicators if indicator in text_lower)
        return noise_count > 1  # Allow one noise word, but not multiple

    def _clean_title(self, title: str) -> str:
        """Clean and format article title with extensive noise removal."""
        import re

        if not title:
            return ""

        # Remove common website navigation and UI elements
        ui_noise_patterns = [
            r'Provide news feedback or report an error',
            r'Send a tip to our reporters',
            r'Most Popular News.*?Opinion',
            r'Read Next.*?Most Popular',
            r'Use Alt \+ Down Arrow to expand',
            r'Subscribe.*?(?:today|now|here)',
            r'Sign up.*?newsletter',
            r'Follow.*?(?:Twitter|Facebook)',
            r'Copyright.*?rights reserved',
            r'Advertisement.*?continue',
            r'Read more.*?here',
            r'Click here.*?more',
            r'View.*?(?:gallery|photos)',
            r'Download.*?app',
            r'Login.*?account',
            r'\s*\*\s*Most Popular.*',
            r'\s*\*\s*Read Next.*',
            r'\s*#\s*.*',
            r'Asia Dow \*.*',
        ]

        cleaned = title
        for pattern in ui_noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove common prefixes and suffixes
        cleaned = re.sub(r'^(Breaking:|BREAKING:|News:|NEWS:|UPDATE:)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*-\s*(Reuters|Bloomberg|WSJ|CNBC|AP|Associated Press).*$', '', cleaned, flags=re.IGNORECASE)

        # Remove extra punctuation and symbols
        cleaned = re.sub(r'[\*#]{1,}', '', cleaned)
        cleaned = re.sub(r'\s*\|\s*.*$', '', cleaned)  # Remove everything after pipe symbol

        # Clean up whitespace and formatting
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Remove trailing periods and other punctuation
        cleaned = cleaned.rstrip('.:;,!?')

        # If the cleaned title is too short, return empty
        if len(cleaned) < 10:
            return ""

        return cleaned

    def _is_valid_title(self, title: str) -> bool:
        """Check if extracted title meets strict quality standards."""
        import re

        if not title or len(title) < 15 or len(title) > 250:
            return False

        # Must contain some alphanumeric content
        if not any(c.isalnum() for c in title):
            return False

        # Must contain at least 3 words
        words = title.split()
        if len(words) < 3:
            return False

        # Should not be primarily navigation or UI text
        navigation_phrases = [
            'click here', 'read more', 'continue reading', 'subscribe',
            'sign up', 'log in', 'home page', 'main page', 'contact us',
            'about us', 'privacy policy', 'terms of service', 'download',
            'register', 'login', 'most popular', 'read next', 'provide news',
            'send a tip', 'advertisement', 'sponsored content', 'view gallery'
        ]

        title_lower = title.lower()
        nav_matches = sum(1 for phrase in navigation_phrases if phrase in title_lower)
        if nav_matches > 0:
            return False

        # Should not be just company names or stock symbols
        if re.match(r'^[A-Z]{2,5}\s*Inc\.?\s*$', title) or re.match(r'^[A-Z]{2,5}\s*Corp\.?\s*$', title):
            return False

        # Should contain some meaningful content indicators
        meaningful_indicators = [
            'reports', 'announces', 'says', 'posts', 'reaches', 'agrees', 'launches',
            'acquires', 'merges', 'earnings', 'revenue', 'profit', 'loss', 'growth',
            'falls', 'rises', 'gains', 'drops', 'beats', 'misses', 'forecast',
            'outlook', 'guidance', 'deal', 'agreement', 'contract', 'partnership',
            'investment', 'funding', 'ipo', 'stock', 'shares', 'market', 'trade'
        ]

        has_meaningful_content = any(indicator in title_lower for indicator in meaningful_indicators)

        # Also check for proper nouns (companies, names) which indicate real news
        proper_noun_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        proper_nouns = re.findall(proper_noun_pattern, title)
        has_proper_nouns = len(proper_nouns) >= 1

        # Title is valid if it has meaningful content OR proper nouns (companies/names)
        return has_meaningful_content or has_proper_nouns

    def _is_quality_news_content(self, content: str, title: str) -> bool:
        """Check if content represents quality news reporting."""
        content_lower = content.lower()

        # Must have substantial content
        if len(content) < 200:
            return False

        # Should contain news-related indicators
        news_indicators = [
            'reported', 'announced', 'said', 'according to', 'sources',
            'statement', 'company', 'market', 'shares', 'stock', 'revenue',
            'earnings', 'financial', 'business', 'industry', 'analyst'
        ]

        indicator_count = sum(1 for indicator in news_indicators if indicator in content_lower)
        if indicator_count < 3:
            return False

        # Should not be primarily promotional content
        promotional_phrases = [
            'buy now', 'sign up', 'subscribe', 'advertisement',
            'sponsored', 'click here', 'limited time'
        ]

        promo_count = sum(1 for phrase in promotional_phrases if phrase in content_lower)
        if promo_count > 2:
            return False

        return True

    def _is_news_article(self, content: str, url: str) -> bool:
        """Check if this is actually a news article vs other content."""
        url_lower = url.lower()

        # Reject non-news URL patterns
        non_news_patterns = [
            '/about', '/contact', '/careers', '/jobs', '/privacy', '/terms',
            '/subscribe', '/login', '/signup', '/home', '/index',
            '/products', '/services', '/solutions'
        ]

        if any(pattern in url_lower for pattern in non_news_patterns):
            return False

        # Look for news article URL patterns
        news_patterns = [
            '/news/', '/article/', '/story/', '/report/', '/press-release/',
            '/market/', '/business/', '/finance/', '/earnings/'
        ]

        has_news_pattern = any(pattern in url_lower for pattern in news_patterns)

        # Also check for date patterns in URL (common in news articles)
        import re
        has_date_pattern = bool(re.search(r'/20\d{2}/', url))

        return has_news_pattern or has_date_pattern

    def _extract_publication_date(self, content: str, url: str) -> Optional[str]:
        """Extract publication date from content or URL."""
        import re
        from datetime import datetime

        # Try to extract date from content
        date_patterns = [
            r'Published[:\s]+(\w+\s+\d{1,2},?\s+20\d{2})',
            r'(\w+\s+\d{1,2},?\s+20\d{2})',
            r'(20\d{2}-\d{2}-\d{2})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content[:1000])
            if match:
                try:
                    date_str = match.group(1)
                    # Basic date parsing - could be enhanced
                    return datetime.now().isoformat()  # Placeholder
                except:
                    continue

        return None

    def _calculate_article_relevance(self, content: str, title: str, query: str, domain: str) -> float:
        """Calculate relevance score based on multiple factors."""
        score = 0.0

        # Base score for premium domains
        premium_scores = {
            'reuters.com': 0.9,
            'bloomberg.com': 0.9,
            'wsj.com': 0.9,
            'ft.com': 0.85,
            'cnbc.com': 0.8,
            'marketwatch.com': 0.8,
            'apnews.com': 0.85
        }

        score = premium_scores.get(domain, 0.7)

        # Bonus for query term matches in title
        query_terms = query.lower().split()
        title_lower = title.lower()
        title_matches = sum(1 for term in query_terms if term in title_lower and len(term) > 2)
        score += min(title_matches * 0.1, 0.2)

        # Bonus for recent content indicators
        content_lower = content.lower()
        recent_indicators = ['today', 'yesterday', 'this week', 'announced', 'reported']
        recent_bonus = sum(0.02 for indicator in recent_indicators if indicator in content_lower)
        score += min(recent_bonus, 0.1)

        return min(score, 1.0)

    def _create_clean_preview(self, content: str) -> str:
        """Create a clean preview of the article content."""
        import re

        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', content).strip()

        # Take first substantial paragraph
        sentences = cleaned.split('. ')
        preview_sentences = []
        char_count = 0

        for sentence in sentences:
            if char_count + len(sentence) > 300:
                break
            if len(sentence.strip()) > 20:  # Substantial sentences only
                preview_sentences.append(sentence.strip())
                char_count += len(sentence)

        preview = '. '.join(preview_sentences)
        if not preview.endswith('.'):
            preview += '.'

        return preview

    def _get_source_display_name(self, domain: str) -> str:
        """Get proper display name for news source."""
        source_names = {
            'reuters.com': 'Reuters',
            'bloomberg.com': 'Bloomberg',
            'wsj.com': 'Wall Street Journal',
            'ft.com': 'Financial Times',
            'cnbc.com': 'CNBC',
            'marketwatch.com': 'MarketWatch',
            'apnews.com': 'Associated Press',
            'barrons.com': "Barron's",
            'businesswire.com': 'Business Wire',
            'prnewswire.com': 'PR Newswire'
        }

        return source_names.get(domain, domain.replace('.com', '').title())

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return "unknown"

    def _curate_and_organize_articles(self, articles: List[Dict], key_points: List[Dict], user_preferences: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Final curation and organization of articles for UI display.

        Args:
            articles: Raw articles from Tavily search
            key_points: Original key points for context
            user_preferences: User preferences for personalization

        Returns:
            Curated and organized articles ready for UI display
        """
        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        # Sort by priority and relevance
        sorted_articles = sorted(
            unique_articles,
            key=lambda x: (x.get('priority', 3), -x.get('relevance_score', 0))
        )

        # Enhance articles for UI display
        curated_articles = []
        for i, article in enumerate(sorted_articles[:20]):  # Limit to top 20
            curated_article = {
                'id': f"tavily_focused_{i}",
                'title': article['title'],
                'url': article['url'],
                'source': article['source'],
                'preview': article['content'],
                'sentiment': 'neutral',  # Could enhance with sentiment analysis
                'tags': self._generate_tags(article),
                'relevance_score': article.get('relevance_score', 0.5),
                'category': 'focused_news',
                'timestamp': article['timestamp'],
                'cluster_info': {
                    'cluster_id': article.get('cluster_id'),
                    'search_query': article.get('search_query'),
                    'ticker': article.get('ticker')
                }
            }
            curated_articles.append(curated_article)

        logger.info(f"🎯 Final curation: {len(curated_articles)} articles ready for UI")
        return curated_articles

    def _create_fallback_articles_from_retriever_results(self, initial_results: Dict[str, Any], key_points: List[Dict]) -> List[Dict[str, Any]]:
        """
        Create formatted articles from initial retriever results when Tavily is unavailable.

        Args:
            initial_results: Results from enhanced planner
            key_points: Key points for context

        Returns:
            List of formatted articles from retriever results
        """
        fallback_articles = []

        # Process articles from different categories
        article_categories = ['financial_news', 'general_news', 'breaking_news']

        for category in article_categories:
            articles = initial_results.get(category, [])

            for i, article in enumerate(articles[:8]):  # Limit to top 8 per category
                if isinstance(article, dict):
                    # Extract and clean article data
                    raw_title = article.get('title', article.get('headline', ''))
                    url = article.get('url', article.get('href', ''))
                    raw_content = article.get('content', article.get('body', article.get('summary', '')))

                    if not raw_title or not url:
                        continue

                    # Clean and format the title
                    clean_title = self._extract_proper_article_title_from_raw(raw_title, raw_content)
                    if not clean_title:
                        clean_title = self._fallback_clean_title(raw_title)

                    # Create a proper summary instead of raw content
                    summary = self._create_article_summary(raw_content, clean_title)

                    # Extract domain and source name
                    domain = self._extract_domain(url)
                    source_name = self._get_source_display_name(domain)

                    # Calculate relevance score
                    relevance_score = self._calculate_fallback_relevance(clean_title, raw_content, key_points)

                    fallback_articles.append({
                        'title': clean_title,
                        'url': url,
                        'content': summary,
                        'source': source_name,
                        'search_query': f"fallback_{category}",
                        'cluster_id': i,
                        'priority': 2 if category == 'financial_news' else 3,
                        'ticker': None,
                        'relevance_score': relevance_score,
                        'timestamp': datetime.now().isoformat(),
                        'source_type': 'retriever_fallback',
                        'domain': domain,
                        'category': category,
                        'quality_validated': False
                    })

        # Sort by relevance and category priority
        fallback_articles = sorted(
            fallback_articles,
            key=lambda x: (x['priority'], -x['relevance_score'])
        )[:15]  # Limit to top 15

        logger.info(f"📰 Created {len(fallback_articles)} fallback articles from retriever results")
        return fallback_articles

    def _extract_proper_article_title_from_raw(self, raw_title: str, content: str) -> Optional[str]:
        """Extract and clean article title from raw title and content."""
        import re

        # First, try to clean the raw title if it's good
        if raw_title and len(raw_title) > 10:
            cleaned_title = self._fallback_clean_title(raw_title)
            if self._is_valid_title(cleaned_title):
                return cleaned_title

        # If raw title is poor, try to extract from content
        if content and len(content) > 50:
            # Look for headline patterns in the first 300 characters
            content_start = content[:300]

            # Pattern for news headlines
            headline_patterns = [
                r'^([A-Z][^.!?]{15,120}[.!?]?)',  # First sentence
                r'([A-Z][A-Za-z\s]+(?:says|reports|announces|posts)[^.!?]{10,80}[.!?]?)',  # News style
                r'([A-Z][A-Za-z\s]*(?:stock|shares|earnings|revenue)[^.!?]{10,100}[.!?]?)',  # Financial news
            ]

            for pattern in headline_patterns:
                matches = re.findall(pattern, content_start)
                for match in matches:
                    clean_title = self._fallback_clean_title(match.strip())
                    if self._is_valid_title(clean_title):
                        return clean_title

        return None

    def _fallback_clean_title(self, title: str) -> str:
        """Clean up raw title for display."""
        import re

        if not title:
            return ""

        # Remove common noise patterns
        noise_patterns = [
            r'\s*\|\s*.*$',  # Remove "| Website Name" suffixes
            r'\s*-\s*.*$',   # Remove "- Website Name" suffixes
            r'^\s*\d+\.\s*', # Remove leading numbers
            r'\s*\(\s*[A-Z]+\s*\)\s*$',  # Remove ticker symbols at end
        ]

        cleaned = title
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned)

        # Apply space normalization
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Truncate very long titles to reasonable length
        if len(cleaned) > 120:
            # Try to truncate at word boundary
            truncated = cleaned[:120]
            last_space = truncated.rfind(' ')
            if last_space > 80:
                cleaned = truncated[:last_space] + '...'
            else:
                cleaned = truncated + '...'

        # Capitalize properly if all caps or all lowercase
        if cleaned.isupper() or cleaned.islower():
            cleaned = cleaned.title()

        return cleaned

    def _create_article_summary(self, content: str, title: str) -> str:
        """Create a clean, readable summary from article content."""
        import re

        if not content:
            return "No summary available."

        # Clean the content
        cleaned = re.sub(r'\s+', ' ', content).strip()

        # Remove common website noise
        noise_patterns = [
            r'cookie\s+policy.*?(?=\.|$)',
            r'privacy\s+policy.*?(?=\.|$)',
            r'subscribe.*?(?=\.|$)',
            r'sign\s+up.*?(?=\.|$)',
            r'follow\s+us.*?(?=\.|$)',
            r'share\s+this.*?(?=\.|$)',
        ]

        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Split into sentences
        sentences = re.split(r'[.!?]+', cleaned)

        # Find the best sentences for summary
        summary_sentences = []
        char_count = 0
        max_chars = 200

        for sentence in sentences:
            sentence = sentence.strip()

            # Skip very short or likely noise sentences
            if len(sentence) < 25:
                continue

            # Skip sentences that are mostly navigation/UI text
            if any(word in sentence.lower() for word in ['click', 'read more', 'continue', 'subscribe', 'download']):
                continue

            # Add sentence if we have room
            if char_count + len(sentence) <= max_chars:
                summary_sentences.append(sentence)
                char_count += len(sentence)
            else:
                break

        # Create final summary
        if summary_sentences:
            summary = '. '.join(summary_sentences)
            if not summary.endswith('.'):
                summary += '.'
            return summary
        else:
            # Fallback: just take first 200 chars and clean up
            fallback = cleaned[:200].strip()
            if len(fallback) > 10:
                # Try to end at sentence boundary
                last_period = fallback.rfind('.')
                if last_period > 100:
                    return fallback[:last_period + 1]
                else:
                    return fallback + '...'
            else:
                return "Summary not available."

    def _calculate_fallback_relevance(self, title: str, content: str, key_points: List[Dict]) -> float:
        """Calculate relevance score for fallback articles."""
        score = 0.5  # Base score

        # Check for matches with key points
        title_lower = title.lower()
        content_lower = content.lower() if content else ""

        key_point_matches = 0
        for kp in key_points:
            kp_query = kp.get('original_title', kp.get('query', '')).lower()
            if any(term in title_lower for term in kp_query.split() if len(term) > 3):
                key_point_matches += 1

        score += min(key_point_matches * 0.1, 0.3)

        # Check for important financial terms
        important_terms = ['earnings', 'revenue', 'stock', 'shares', 'government', 'deal', 'merger', 'AI', 'technology']
        term_matches = sum(1 for term in important_terms if term.lower() in title_lower)
        score += min(term_matches * 0.05, 0.2)

        return min(score, 1.0)

    def _generate_tags(self, article: Dict) -> List[str]:
        """Generate tags for an article based on its content and metadata."""
        tags = []

        # Add ticker tag if available
        if article.get('ticker'):
            tags.append(article['ticker'])

        # Add source tag
        source = article.get('source', '')
        if source:
            tags.append(source.replace('.com', ''))

        # Add content-based tags (simplified)
        content = article.get('content', '').lower()

        tag_keywords = {
            'earnings': 'earnings',
            'acquisition': 'M&A',
            'ipo': 'IPO',
            'revenue': 'revenue',
            'profit': 'profit',
            'loss': 'loss',
            'growth': 'growth',
            'decline': 'decline',
            'innovation': 'innovation',
            'technology': 'tech',
            'ai': 'AI',
            'artificial intelligence': 'AI'
        }

        for keyword, tag in tag_keywords.items():
            if keyword in content:
                tags.append(tag)

        return tags[:5]  # Limit to 5 tags

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the pipeline."""
        return {
            'enhanced_planner_available': self.enhanced_planner is not None,
            'tavily_api_configured': bool(self.tavily_api_key),
            'gemini_api_configured': bool(self.gemini_api_key)
        }

    def cleanup(self):
        """Cleanup pipeline resources."""
        try:
            if self.enhanced_planner:
                self.enhanced_planner.cleanup()
            logger.info("Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during pipeline cleanup: {e}")


# Factory function for easy integration
def create_enhanced_news_pipeline(gemini_api_key: str, tavily_api_key: str, max_retrievers: int = 5) -> EnhancedNewsDiscoveryPipeline:
    """
    Create an enhanced news discovery pipeline.

    Args:
        gemini_api_key: API key for Gemini AI
        tavily_api_key: API key for Tavily search
        max_retrievers: Maximum concurrent retrievers

    Returns:
        Configured EnhancedNewsDiscoveryPipeline
    """
    return EnhancedNewsDiscoveryPipeline(gemini_api_key, tavily_api_key, max_retrievers)


# Example usage and testing
async def test_enhanced_pipeline():
    """Test the enhanced news discovery pipeline."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not gemini_key or not tavily_key:
        print("ERROR: GEMINI_API_KEY and TAVILY_API_KEY are required")
        return

    # Create pipeline
    pipeline = create_enhanced_news_pipeline(gemini_key, tavily_key, max_retrievers=3)

    # Test query
    test_query = "Tesla autonomous driving latest developments"
    user_prefs = {
        'watchlist': ['TSLA', 'AAPL', 'GOOGL'],
        'topics': ['technology', 'automotive'],
        'keywords': ['autonomous', 'AI', 'innovation']
    }

    print(f"Testing Enhanced News Discovery Pipeline...")
    print(f"Query: {test_query}")

    try:
        results = await pipeline.discover_news(test_query, user_prefs)

        print(f"\n🎯 PIPELINE RESULTS:")
        print(f"Total Duration: {results['processing_stats']['total_duration']:.2f}s")
        print(f"Final Articles: {len(results['final_articles'])}")

        # Show stage breakdown
        for stage_name, stage_info in results['stages'].items():
            print(f"{stage_name}: {stage_info['duration']:.2f}s")

        # Show final articles
        print(f"\n📰 FINAL CURATED ARTICLES:")
        for i, article in enumerate(results['final_articles'][:5]):
            print(f"{i+1}. {article['title']}")
            print(f"   Source: {article['source']} | Score: {article['relevance_score']:.2f}")
            print(f"   Tags: {', '.join(article['tags'])}")
            print(f"   URL: {article['url'][:60]}...")
            print()

        pipeline.cleanup()

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_enhanced_pipeline())