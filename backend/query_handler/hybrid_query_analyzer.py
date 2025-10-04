"""
Hybrid Query Analyzer - Combines multiple NER/extraction methods
Handles natural language queries and extracts structured information for database querying
"""

import re
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Try to import spaCy (optional)
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed. Install with: pip install spacy")

# Try to import TextBlob (optional)
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("TextBlob not installed. Install with: pip install textblob")


@dataclass
class QueryIntent:
    """Structured representation of extracted query information"""
    original_query: str
    companies: List[str]
    tickers: List[str]
    topics: List[str]
    products: List[str]
    people: List[str]
    time_context: Optional[str]
    intent: Optional[str]
    keywords: List[str]
    financial_terms: List[str]
    confidence: float

    def to_dict(self) -> Dict:
        return asdict(self)


class HybridQueryAnalyzer:
    """
    Hybrid NER and keyword extraction using multiple methods:
    1. Regex for ticker symbols (fast)
    2. spaCy for named entity recognition (medium speed, good accuracy)
    3. TextBlob for keyword extraction (fast, basic)
    4. LLM (Gemini) for complex queries (slow, high accuracy)
    """

    def __init__(self, gemini_api_key: str):
        """Initialize the hybrid analyzer with Gemini API key"""
        self.gemini_api_key = gemini_api_key

        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Ticker regex pattern (1-5 uppercase letters)
        self.ticker_pattern = re.compile(r'\b[A-Z]{1,5}\b')

        # Common false positive words to filter
        self.common_words = {
            'I', 'A', 'AND', 'OR', 'THE', 'IS', 'IT', 'IN', 'ON', 'AT', 'TO',
            'Q', 'US', 'AM', 'PM', 'VS', 'BY', 'FOR', 'OF', 'AS', 'AN'
        }

        # Financial keywords dictionary
        self.financial_keywords = {
            'earnings', 'revenue', 'profit', 'loss', 'sales', 'growth',
            'quarter', 'Q1', 'Q2', 'Q3', 'Q4', 'guidance', 'forecast',
            'merger', 'acquisition', 'IPO', 'stock', 'shares', 'dividend',
            'buyback', 'cash flow', 'EBITDA', 'margin', 'debt', 'equity',
            'valuation', 'market cap', 'capitalization', 'expansion',
            'launch', 'product', 'service', 'strategy', 'competition'
        }

        logger.info(f"HybridQueryAnalyzer initialized (spaCy: {SPACY_AVAILABLE}, TextBlob: {TEXTBLOB_AVAILABLE})")

    def analyze_query(self, query: str) -> QueryIntent:
        """
        Analyze user query using hybrid approach

        Flow:
        1. Run fast methods (regex, spaCy, TextBlob)
        2. Calculate confidence
        3. If confidence < threshold, use LLM fallback
        4. Merge and return results
        """
        result = {
            'original_query': query,
            'companies': [],
            'tickers': [],
            'topics': [],
            'products': [],
            'people': [],
            'time_context': None,
            'intent': None,
            'keywords': [],
            'financial_terms': [],
            'confidence': 0.0
        }

        # ===== STAGE 1: FAST METHODS =====

        # Method 1: Regex ticker extraction (~5ms)
        potential_tickers = self._extract_tickers(query)
        result['tickers'].extend(potential_tickers)

        # Method 2: spaCy NER (~30-50ms)
        if SPACY_AVAILABLE:
            spacy_entities = self._extract_with_spacy(query)
            result['companies'].extend(spacy_entities.get('companies', []))
            result['products'].extend(spacy_entities.get('products', []))
            result['people'].extend(spacy_entities.get('people', []))
            if spacy_entities.get('time_context'):
                result['time_context'] = spacy_entities['time_context']

        # Method 3: TextBlob keywords (~20ms)
        if TEXTBLOB_AVAILABLE:
            textblob_keywords = self._extract_with_textblob(query)
            result['keywords'].extend(textblob_keywords)

        # Method 4: Financial term detection (~1ms)
        result['financial_terms'] = self._extract_financial_terms(query)

        # Calculate confidence from fast methods
        result['confidence'] = self._calculate_confidence(result)

        # ===== STAGE 2: LLM FALLBACK (if needed) =====

        # Use LLM if confidence is low or no company found
        if result['confidence'] < 0.7 or not result['companies']:
            logger.info(f"Confidence {result['confidence']:.2f} < 0.7, using LLM fallback")
            llm_result = self._extract_with_llm(query)
            if llm_result:
                result = self._merge_results(result, llm_result)
                result['confidence'] = min(result['confidence'] + 0.2, 1.0)  # Boost confidence

        # Clean and deduplicate
        result = self._clean_and_deduplicate(result)

        # Recalculate final confidence
        result['confidence'] = self._calculate_confidence(result)

        return QueryIntent(**result)

    def _extract_tickers(self, query: str) -> List[str]:
        """Extract ticker symbols using regex"""
        matches = self.ticker_pattern.findall(query)
        # Filter out common words
        tickers = [m for m in matches if m not in self.common_words]
        return tickers

    def _extract_with_spacy(self, query: str) -> Dict:
        """Extract entities using spaCy NER"""
        if not SPACY_AVAILABLE:
            return {}

        doc = nlp(query)
        entities = {
            'companies': [],
            'products': [],
            'people': [],
            'time_context': None
        }

        for ent in doc.ents:
            if ent.label_ == "ORG":  # Organizations
                entities['companies'].append(ent.text)
            elif ent.label_ == "PRODUCT":
                entities['products'].append(ent.text)
            elif ent.label_ == "PERSON":
                entities['people'].append(ent.text)
            elif ent.label_ == "DATE" and not entities['time_context']:
                entities['time_context'] = ent.text

        return entities

    def _extract_with_textblob(self, query: str) -> List[str]:
        """Extract keywords using TextBlob"""
        if not TEXTBLOB_AVAILABLE:
            return []

        blob = TextBlob(query)

        # Extract noun phrases
        noun_phrases = list(blob.noun_phrases)

        # Extract important nouns
        keywords = [word for word, tag in blob.tags
                   if tag in ['NN', 'NNP', 'NNPS', 'NNS']]

        return noun_phrases + keywords

    def _extract_financial_terms(self, query: str) -> List[str]:
        """Extract financial keywords from query"""
        query_lower = query.lower()
        found_terms = []

        for term in self.financial_keywords:
            if term.lower() in query_lower:
                found_terms.append(term)

        return found_terms

    def _extract_with_llm(self, query: str) -> Optional[Dict]:
        """Use Gemini LLM for complex extraction"""
        prompt = f"""
You are a financial query analyzer. Extract structured information from this query.

Query: "{query}"

Return ONLY valid JSON with this structure:
{{
    "companies": ["company names found"],
    "tickers": ["stock ticker symbols"],
    "topics": ["main topics or themes"],
    "products": ["specific products mentioned"],
    "intent": "what the user wants to know (e.g., earnings_report, product_news, market_analysis, company_strategy)",
    "keywords": ["relevant search terms"]
}}

Rules:
- If you recognize a product, infer its company (e.g., "iPhone" → company: "Apple", ticker: "AAPL")
- For well-known companies, include their ticker symbol
- Topics should be specific and searchable (e.g., "chip design", "sales performance")
- Intent should be one word or short phrase

Return only the JSON, no explanation.
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Low temperature for consistency
                    max_output_tokens=500
                )
            )

            # Parse JSON response
            text = response.text.strip()
            # Remove markdown code blocks if present
            text = re.sub(r'```json\s*|\s*```', '', text)
            llm_data = json.loads(text)

            logger.debug(f"LLM extraction successful: {llm_data}")
            return llm_data

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    def _merge_results(self, base: Dict, llm_result: Dict) -> Dict:
        """Merge LLM results with base results"""
        for key in ['companies', 'tickers', 'topics', 'products', 'keywords']:
            if key in llm_result and llm_result[key]:
                base[key].extend(llm_result[key])

        # LLM intent takes priority
        if 'intent' in llm_result and llm_result['intent']:
            base['intent'] = llm_result['intent']

        return base

    def _clean_and_deduplicate(self, result: Dict) -> Dict:
        """Remove duplicates and clean data"""
        for key in ['companies', 'tickers', 'topics', 'products', 'keywords', 'financial_terms']:
            if key in result and result[key]:
                # Remove duplicates while preserving order
                seen = set()
                cleaned = []
                for item in result[key]:
                    item_lower = str(item).lower()
                    if item_lower not in seen:
                        seen.add(item_lower)
                        cleaned.append(item)
                result[key] = cleaned

        return result

    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate confidence score based on extracted information"""
        score = 0.0

        # Strong signals
        if result.get('companies') or result.get('tickers'):
            score += 0.4

        if result.get('topics') or len(result.get('keywords', [])) >= 2:
            score += 0.3

        if result.get('intent'):
            score += 0.2

        if result.get('financial_terms'):
            score += 0.1

        return min(score, 1.0)
