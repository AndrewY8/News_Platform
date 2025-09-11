"""
Text preprocessing and normalization pipeline for the News Aggregator.

This module provides comprehensive text cleaning and normalization capabilities
including HTML removal, boilerplate detection, language detection, and content chunking.
"""

import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from langdetect import detect, DetectorFactory
    # Set seed for consistent language detection
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

from .models import ContentChunk, ChunkMetadata, SourceType, ReliabilityTier
from .config import PreprocessingConfig

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """
    Comprehensive text preprocessing pipeline for news content.
    
    Features:
    - HTML tag removal and text extraction
    - Boilerplate content detection and removal
    - URL, email, phone number cleaning
    - Whitespace normalization
    - Language detection
    - Content chunking for large texts
    - Duplicate detection and removal
    """
    
    def __init__(self, config: PreprocessingConfig):
        """
        Initialize the text preprocessor.
        
        Args:
            config: Preprocessing configuration parameters
        """
        self.config = config
        self._setup_regex_patterns()
        self._setup_boilerplate_patterns()
        
        if not BS4_AVAILABLE and config.remove_html:
            logger.warning("BeautifulSoup not available, HTML removal will use regex fallback")
        
        if not LANGDETECT_AVAILABLE and config.language_detection:
            logger.warning("langdetect not available, language detection disabled")
        
        if not FUZZYWUZZY_AVAILABLE:
            logger.warning("fuzzywuzzy not available, fuzzy matching disabled")
    
    def _setup_regex_patterns(self):
        """Setup compiled regex patterns for efficient text processing."""
        # URL pattern
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Phone pattern (US format)
        self.phone_pattern = re.compile(
            r'(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        )
        
        # HTML pattern (fallback if BeautifulSoup not available)
        self.html_pattern = re.compile(r'<[^>]+>')
        
        # Multiple whitespace pattern
        self.whitespace_pattern = re.compile(r'\s+')
        
        # Social media patterns
        self.hashtag_pattern = re.compile(r'#\w+')
        self.mention_pattern = re.compile(r'@\w+')
        
        # Common noise patterns
        self.noise_patterns = [
            re.compile(r'\b(click here|read more|learn more|see more)\b', re.IGNORECASE),
            re.compile(r'\b(advertisement|sponsored|ad)\b', re.IGNORECASE),
            re.compile(r'\b(subscribe|newsletter|unsubscribe)\b', re.IGNORECASE),
        ]
    
    def _setup_boilerplate_patterns(self):
        """Setup patterns for common boilerplate content."""
        self.boilerplate_patterns = [
            # Copyright notices
            re.compile(r'©\s*\d{4}.*?(?:\.|$)', re.IGNORECASE),
            re.compile(r'copyright\s+\d{4}.*?(?:\.|$)', re.IGNORECASE),
            
            # Newsletter/subscription boilerplate
            re.compile(r'to unsubscribe.*?(?:\.|$)', re.IGNORECASE),
            re.compile(r'this email was sent.*?(?:\.|$)', re.IGNORECASE),
            re.compile(r'if you.*?unsubscribe.*?(?:\.|$)', re.IGNORECASE),
            
            # Navigation elements
            re.compile(r'home\s+about\s+contact', re.IGNORECASE),
            re.compile(r'privacy\s+policy', re.IGNORECASE),
            re.compile(r'terms\s+of\s+service', re.IGNORECASE),
            
            # Social media boilerplate
            re.compile(r'follow us on.*?(?:\.|$)', re.IGNORECASE),
            re.compile(r'like us on facebook', re.IGNORECASE),
            re.compile(r'share\s+tweet\s+email', re.IGNORECASE),
        ]
    
    def clean_html(self, text: str) -> str:
        """
        Remove HTML tags and extract clean text.
        
        Args:
            text: Raw text potentially containing HTML
            
        Returns:
            Clean text with HTML removed
        """
        if not text:
            return ""
        
        if BS4_AVAILABLE:
            try:
                soup = BeautifulSoup(text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "meta", "link"]):
                    script.decompose()
                
                # Get text and clean up
                clean_text = soup.get_text()
                
                # Clean up lines (remove excessive newlines)
                lines = (line.strip() for line in clean_text.splitlines())
                clean_text = '\n'.join(line for line in lines if line)
                
                return clean_text
                
            except Exception as e:
                logger.warning(f"BeautifulSoup failed, using regex fallback: {e}")
        
        # Fallback to regex-based HTML removal
        clean_text = self.html_pattern.sub(' ', text)
        return clean_text
    
    def remove_boilerplate(self, text: str) -> str:
        """
        Remove common boilerplate content from text.
        
        Args:
            text: Input text
            
        Returns:
            Text with boilerplate content removed
        """
        if not text:
            return ""
        
        clean_text = text
        
        # Remove known boilerplate patterns
        for pattern in self.boilerplate_patterns:
            clean_text = pattern.sub(' ', clean_text)
        
        # Remove noise patterns
        for pattern in self.noise_patterns:
            clean_text = pattern.sub(' ', clean_text)
        
        return clean_text
    
    def clean_content(self, text: str) -> str:
        """
        Apply all content cleaning operations.
        
        Args:
            text: Raw input text
            
        Returns:
            Cleaned and normalized text
        """
        if not text:
            return ""
        
        clean_text = text
        
        # Remove HTML if enabled
        if self.config.remove_html:
            clean_text = self.clean_html(clean_text)
        
        # Remove URLs if enabled
        if self.config.remove_urls:
            clean_text = self.url_pattern.sub(' ', clean_text)
        
        # Remove emails if enabled
        if self.config.remove_email:
            clean_text = self.email_pattern.sub(' ', clean_text)
        
        # Remove phone numbers if enabled
        if self.config.remove_phone:
            clean_text = self.phone_pattern.sub(' ', clean_text)
        
        # Remove boilerplate if enabled
        if self.config.remove_boilerplate:
            clean_text = self.remove_boilerplate(clean_text)
        
        # Normalize whitespace if enabled
        if self.config.normalize_whitespace:
            clean_text = self.whitespace_pattern.sub(' ', clean_text).strip()
        
        return clean_text
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the text.
        
        Args:
            text: Input text
            
        Returns:
            ISO 639-1 language code (defaults to 'en' if detection fails)
        """
        if not LANGDETECT_AVAILABLE or not text:
            return "en"
        
        try:
            # Use first 1000 characters for language detection
            sample = text[:1000].strip()
            if len(sample) < 20:  # Too short for reliable detection
                return "en"
            
            detected_lang = detect(sample)
            
            # Validate against supported languages
            if detected_lang in self.config.supported_languages:
                return detected_lang
            else:
                logger.debug(f"Detected language '{detected_lang}' not in supported languages")
                return "en"
                
        except Exception as e:
            logger.debug(f"Language detection failed: {e}")
            return "en"
    
    def chunk_text(self, text: str, max_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """
        Split text into smaller chunks for processing.
        
        Args:
            text: Input text to chunk
            max_size: Maximum chunk size (uses config if not provided)
            overlap: Overlap between chunks (uses config if not provided)
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        max_size = max_size or self.config.max_chunk_size
        overlap = overlap or self.config.chunk_overlap
        
        # If text is smaller than max size, return as single chunk
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + max_size
            
            # If we're not at the end, try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending in the last 100 characters
                search_start = max(start, end - 100)
                sentence_end = -1
                
                for i in range(end, search_start, -1):
                    if text[i] in '.!?':
                        # Make sure it's not an abbreviation
                        if i < len(text) - 1 and text[i + 1].isspace():
                            sentence_end = i + 1
                            break
                
                if sentence_end > 0:
                    end = sentence_end
            
            # Extract chunk
            chunk = text[start:end].strip()
            if len(chunk) >= self.config.min_sentence_length:
                chunks.append(chunk)
            
            # Move start position (with overlap)
            start = end - overlap
            
            # Avoid infinite loop
            if start <= 0:
                break
        
        return chunks
    
    def classify_source_type(self, url: str, title: str, content: str) -> SourceType:
        """
        Classify the type of content source.
        
        Args:
            url: Source URL
            title: Content title
            content: Content text
            
        Returns:
            Classified source type
        """
        if not url:
            return SourceType.GENERAL_NEWS
        
        url_lower = url.lower()
        title_lower = title.lower() if title else ""
        content_lower = content[:500].lower() if content else ""  # First 500 chars
        
        # SEC filings
        if any(domain in url_lower for domain in ['sec.gov', 'edgar']):
            return SourceType.SEC_FILING
        
        # Breaking news indicators
        breaking_indicators = ['breaking', 'urgent', 'developing', 'just in', 'live update', 'alert']
        if any(indicator in title_lower or indicator in content_lower for indicator in breaking_indicators):
            return SourceType.BREAKING_NEWS
        
        # Financial news indicators
        financial_indicators = ['earnings', 'quarterly', 'financial results', 'revenue', 'profit', 'stock', 'market']
        if any(indicator in title_lower or indicator in content_lower for indicator in financial_indicators):
            return SourceType.FINANCIAL_NEWS
        
        # Social media
        social_domains = ['twitter.com', 'facebook.com', 'instagram.com', 'linkedin.com', 'reddit.com']
        if any(domain in url_lower for domain in social_domains):
            return SourceType.SOCIAL_MEDIA
        
        # Blog posts
        blog_indicators = ['blog', 'medium.com', 'substack.com', 'wordpress']
        if any(indicator in url_lower for indicator in blog_indicators):
            return SourceType.BLOG_POST
        
        # Press releases
        pr_indicators = ['press release', 'pr newswire', 'business wire', 'marketwatch']
        if any(indicator in url_lower or indicator in title_lower for indicator in pr_indicators):
            return SourceType.PRESS_RELEASE
        
        return SourceType.GENERAL_NEWS
    
    def classify_reliability_tier(self, source_domain: str) -> ReliabilityTier:
        """
        Classify source reliability based on domain.
        
        Args:
            source_domain: Domain name of the source
            
        Returns:
            Reliability tier classification
        """
        if not source_domain:
            return ReliabilityTier.TIER_5
        
        domain = source_domain.lower()
        
        # Tier 1: Official sources
        tier_1_domains = [
            'sec.gov', 'investor.gov', 'treasury.gov', 'federalreserve.gov',
            'nyse.com', 'nasdaq.com'
        ]
        if any(d in domain for d in tier_1_domains):
            return ReliabilityTier.TIER_1
        
        # Tier 2: Major news agencies
        tier_2_domains = [
            'reuters.com', 'bloomberg.com', 'ap.org', 'apnews.com',
            'marketwatch.com', 'barrons.com'
        ]
        if any(d in domain for d in tier_2_domains):
            return ReliabilityTier.TIER_2
        
        # Tier 3: Established media
        tier_3_domains = [
            'cnn.com', 'cnbc.com', 'wsj.com', 'nytimes.com', 'ft.com',
            'economist.com', 'forbes.com', 'fortune.com'
        ]
        if any(d in domain for d in tier_3_domains):
            return ReliabilityTier.TIER_3
        
        # Tier 4: Smaller outlets
        tier_4_domains = [
            'yahoo.com', 'msn.com', 'businessinsider.com', 'techcrunch.com',
            'seekingalpha.com', 'motleyfool.com'
        ]
        if any(d in domain for d in tier_4_domains):
            return ReliabilityTier.TIER_4
        
        # Default to Tier 5
        return ReliabilityTier.TIER_5
    
    def process_planner_result_item(self, item: Dict[str, Any], source_category: str) -> Optional[ContentChunk]:
        """
        Process a single item from PlannerAgent results into a ContentChunk.
        
        Args:
            item: Dictionary containing article data from PlannerAgent
            source_category: Category from PlannerAgent ('breaking_news', 'financial_news', etc.)
            
        Returns:
            Processed ContentChunk or None if processing fails
        """
        try:
            # Extract basic information
            title = item.get('title', '')
            url = item.get('url', '')
            description = item.get('description', '')
            source_retriever = item.get('source_retriever', 'unknown')
            
            # Use scraped content if available, otherwise use description
            raw_content = item.get('raw_content') or description
            if not raw_content or len(raw_content) < self.config.min_content_length:
                logger.debug(f"Skipping item with insufficient content: {url}")
                return None
            
            # Clean and process content
            processed_content = self.clean_content(raw_content)
            if not processed_content or len(processed_content) < self.config.min_content_length:
                logger.debug(f"Skipping item after cleaning: {url}")
                return None
            
            # Detect language
            language = self.detect_language(processed_content) if self.config.language_detection else "en"
            
            # Extract domain for reliability classification
            source_domain = ""
            try:
                parsed_url = urlparse(url)
                source_domain = parsed_url.netloc
            except Exception:
                pass
            
            # Classify source type and reliability
            source_type = self.classify_source_type(url, title, processed_content)
            reliability_tier = self.classify_reliability_tier(source_domain)
            
            # Parse timestamp (if available)
            timestamp = datetime.utcnow()  # Default to now
            if 'published_date' in item or 'timestamp' in item:
                try:
                    date_str = item.get('published_date') or item.get('timestamp')
                    if isinstance(date_str, str):
                        # Try common date formats
                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                            try:
                                timestamp = datetime.strptime(date_str.split('.')[0].split('+')[0], fmt)
                                break
                            except ValueError:
                                continue
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp: {e}")
            
            # Extract ticker from content or metadata
            ticker = self._extract_ticker(processed_content, item)
            
            # Create metadata
            metadata = ChunkMetadata(
                timestamp=timestamp,
                source=source_domain or "unknown",
                url=url,
                title=title,
                topic=self._extract_topic(processed_content, source_category),
                source_type=source_type,
                reliability_tier=reliability_tier,
                source_retriever=source_retriever,
                ticker=ticker,
                author=item.get('author'),
                language=language,
                word_count=len(processed_content.split()),
                image_urls=item.get('image_urls', [])
            )
            
            # Create content chunk
            chunk = ContentChunk(
                id="",  # Will be generated in __post_init__
                content=raw_content,
                processed_content=processed_content,
                metadata=metadata
            )
            
            return chunk
            
        except Exception as e:
            logger.error(f"Failed to process item {item.get('url', 'unknown')}: {e}")
            return None
    
    def _extract_ticker(self, content: str, item: Dict[str, Any]) -> Optional[str]:
        """Extract stock ticker from content or metadata."""
        # Check if ticker is in metadata
        if 'ticker' in item:
            return item['ticker']
        
        # Look for ticker patterns in content (e.g., AAPL, TSLA, etc.)
        ticker_pattern = re.compile(r'\b[A-Z]{1,5}\b')
        potential_tickers = ticker_pattern.findall(content[:500])  # First 500 chars
        
        # Filter out common words that might match pattern
        common_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'HAS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE'}
        
        for ticker in potential_tickers:
            if ticker not in common_words and len(ticker) >= 2:
                return ticker
        
        return None
    
    def _extract_topic(self, content: str, source_category: str) -> str:
        """Extract main topic from content."""
        # Use source category as base topic
        if source_category == 'breaking_news':
            return 'breaking_news'
        elif source_category == 'financial_news':
            return 'finance'
        elif source_category == 'sec_filings':
            return 'regulatory'
        else:
            return 'general_news'
    
    def process_planner_results(self, planner_results: Dict[str, Any]) -> List[ContentChunk]:
        """
        Process complete PlannerAgent results into ContentChunks.
        
        Args:
            planner_results: Complete results from PlannerAgent
            
        Returns:
            List of processed ContentChunks
        """
        chunks = []
        
        # Process each category
        categories = ['breaking_news', 'financial_news', 'sec_filings', 'general_news']
        
        for category in categories:
            if category not in planner_results:
                continue
            
            items = planner_results[category]
            logger.info(f"Processing {len(items)} items from {category}")
            
            for item in items:
                chunk = self.process_planner_result_item(item, category)
                if chunk:
                    chunks.append(chunk)
        
        logger.info(f"Successfully processed {len(chunks)} content chunks")
        return chunks
