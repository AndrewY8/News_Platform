# Intelligent Query System Documentation

## Overview

The Intelligent Query System enables natural language search across your financial news database using:
- **NER (Named Entity Recognition)** to extract companies, tickers, and topics
- **Semantic embeddings** to match queries to existing research topics
- **Smart caching** to return pre-computed research when available
- **Automatic fallback** to fresh searches when needed

## Architecture

```
User Query: "What's happening with Apple's Vision Pro sales?"
                    ↓
        ┌───────────────────────────────┐
        │  1. Hybrid Query Analyzer     │
        │  - Regex (tickers)             │
        │  - spaCy NER (entities)        │
        │  - TextBlob (keywords)         │
        │  - Gemini LLM (complex cases) │
        └───────────────┬───────────────┘
                        ↓
                 QueryIntent {
                   companies: ["Apple"],
                   tickers: ["AAPL"],
                   topics: ["Vision Pro", "sales"],
                   confidence: 0.92
                 }
                        ↓
        ┌───────────────────────────────┐
        │  2. Database Topic Lookup     │
        │  - Get company's topics        │
        │  - Generate embeddings         │
        │  - Match using cosine similarity│
        └───────────────┬───────────────┘
                        ↓
              Match Found? (similarity > 0.75)
                ┌───────┴───────┐
               YES             NO
                │               │
        ┌───────▼──────┐  ┌────▼────────┐
        │ Return Cached│  │ Trigger     │
        │ Articles     │  │ Fresh Search│
        └──────────────┘  └─────────────┘
```

## System Components

### 1. Hybrid Query Analyzer (`hybrid_query_analyzer.py`)

Extracts structured information from natural language queries.

**Methods used (in order):**

1. **Regex Pattern Matching** (~5ms)
   - Extracts ticker symbols like AAPL, TSLA, MSFT
   - Fast but only catches explicit tickers

2. **spaCy NER** (~30-50ms)
   - Identifies companies, products, people, dates
   - Good accuracy for well-known entities
   - Requires: `python -m spacy download en_core_web_sm`

3. **TextBlob Keywords** (~20ms)
   - Extracts noun phrases and keywords
   - Simple but effective for general terms

4. **Gemini LLM Fallback** (~1-2s, only if confidence < 0.7)
   - Used for complex or ambiguous queries
   - High accuracy, handles inference (e.g., "Vision Pro" → Apple)
   - Cost: ~$0.0001 per query

**Output:**
```python
QueryIntent(
    companies=['Apple'],
    tickers=['AAPL'],
    topics=['Vision Pro sales', 'product performance'],
    products=['Vision Pro'],
    intent='product_news',
    keywords=['sales', 'performance'],
    confidence=0.92
)
```

### 2. Topic Matcher (`intelligent_query_router.py`)

Matches extracted query topics to existing database topics using semantic embeddings.

**Key Features:**
- Generates embeddings for topics on-the-fly (first time)
- Caches embeddings for performance
- Uses cosine similarity for matching
- Threshold: 0.75 (configurable)

**Database Handling:**
- ✅ **Handles empty ticker column**: Queries use company `name` column
- ✅ **Generates topic embeddings**: Creates embeddings from topic name + description
- ✅ **Cache-first approach**: Returns cached results when similarity > 0.75

### 3. Intelligent Query Router

Main orchestrator that coordinates all components.

**Flow:**
1. Analyze query → Extract structured data
2. Determine target company
3. Lookup company's existing topics
4. Generate embeddings and match
5. Return cached OR trigger fresh search

## API Usage

### Endpoint: `/api/articles/search`

**Basic Usage:**
```bash
curl "http://localhost:8004/api/articles/search?q=Tesla earnings Q4"
```

**Response (Cache Hit):**
```json
[
  {
    "id": "abc123",
    "title": "Tesla Q4 2024 Earnings Beat Expectations",
    "source": "Bloomberg",
    "url": "https://...",
    "date": "2024-01-15",
    "preview": "Tesla reported strong Q4 earnings...",
    "relevance_score": 0.92,
    "cached": true,
    "tags": ["Tesla", "Q4 Earnings Report"]
  }
]
```

**Response (Fresh Search Needed):**
```json
{
  "status": "fresh_search_needed",
  "message": "No cached research found. New search needed for Tesla",
  "query_intent": {
    "companies": ["Tesla"],
    "tickers": ["TSLA"],
    "topics": ["earnings", "Q4"],
    "intent": "earnings_report"
  },
  "search_params": {
    "company": "TSLA",
    "topics": ["earnings", "Q4"],
    "keywords": ["earnings", "quarter", "financial"]
  },
  "articles": [ /* fallback articles */ ]
}
```

## Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Required for database features
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Similarity Threshold

Adjust in `intelligent_query_router.py`:

```python
matched_topic = self.topic_matcher.match_query_to_topics(
    query_topics=query_intent.topics,
    existing_topics=company_topics,
    threshold=0.75  # ← Adjust here
)
```

**Recommendations:**
- **0.85+**: Very strict, fewer false positives, more fresh searches
- **0.75**: Balanced (default)
- **0.65**: Looser, more cache hits, some false positives

## Performance Metrics

### Query Analysis Speed

| Method | Speed | Accuracy | When Used |
|--------|-------|----------|-----------|
| Regex | ~5ms | 60% | Always (ticker extraction) |
| spaCy | ~40ms | 75% | Always (entity recognition) |
| TextBlob | ~20ms | 65% | Always (keywords) |
| Gemini LLM | ~1500ms | 95% | Only if confidence < 0.7 |

**Typical Query:**
- Fast path (no LLM): ~70ms
- With LLM fallback: ~1600ms
- LLM usage rate: ~30% of queries

### Cache Hit Rate

Expected cache hit rates:
- **Well-defined queries** (e.g., "Tesla earnings"): 80-90%
- **Product-specific** (e.g., "iPhone 15 sales"): 70-80%
- **Vague queries** (e.g., "tech news"): 20-30%

## Example Queries

### 1. Direct Company Query
```
Query: "AAPL earnings report"

Analysis:
  - Ticker: AAPL (regex)
  - Topics: earnings, report
  - Confidence: 0.9

Database Lookup:
  - Company: Apple
  - Existing topics: ["Q4 2024 Earnings", "Revenue Growth", ...]

Match:
  - "Q4 2024 Earnings" (similarity: 0.91) ✅

Result: Cache hit, 15 articles returned
```

### 2. Product Query (Inference)
```
Query: "What's happening with Vision Pro sales?"

Analysis (uses LLM):
  - Company: Apple (inferred from "Vision Pro")
  - Ticker: AAPL
  - Topics: Vision Pro, sales, product performance
  - Confidence: 0.88

Match:
  - "Vision Pro Launch & Market Reception" (similarity: 0.87) ✅

Result: Cache hit, 12 articles returned
```

### 3. No Match (Fresh Search)
```
Query: "Apple's new AI chip architecture details"

Analysis:
  - Company: Apple
  - Topics: AI chip, architecture
  - Confidence: 0.85

Match:
  - "M3 Chip Development" (similarity: 0.68) ❌
  - "AI Features in iOS" (similarity: 0.71) ❌

Result: No match, trigger fresh search
```

## Handling Database Schema Issues

### Issue 1: Ticker Column Empty

**Problem:** Company tickers stored in `name` column, not `ticker` column.

**Solution:**
```python
def _determine_company(self, query_intent: QueryIntent) -> Optional[str]:
    # Prefer ticker if available
    if query_intent.tickers:
        return query_intent.tickers[0].upper()

    # Fall back to company name
    if query_intent.companies:
        return query_intent.companies[0]
```

Query uses `name` column for lookups:
```python
topics = self.research_db.get_company_topics(company_name=company)
```

### Issue 2: Topics Not Embedded

**Problem:** Topic `name` and `description` fields don't have pre-computed embeddings.

**Solution:** Generate embeddings on-demand:
```python
def generate_topic_embedding(self, topic_name: str, topic_description: str = "") -> np.ndarray:
    composite_text = f"{topic_name} {topic_description}"

    # Check cache first
    if composite_text in self.embedding_cache:
        return self.embedding_cache[composite_text]

    # Generate and cache
    embedding = self.model.encode(composite_text)
    self.embedding_cache[composite_text] = embedding

    return embedding
```

**Performance:**
- First query: ~100ms (generate embedding)
- Subsequent queries: ~1ms (cached)

## Fallback Strategy

When no good topic match is found:

### Option 1: Return Search Parameters
```json
{
  "status": "fresh_search_needed",
  "search_params": {
    "company": "Tesla",
    "topics": ["chip shortage", "supply chain"],
    "keywords": ["semiconductor", "manufacturing"]
  }
}
```

Frontend or background job can:
1. Trigger `OrchestratorAgent` with these params
2. Store new research in database
3. Return results to user

### Option 2: Immediate Search (Future)
```python
# In intelligent_query_router.py
if no_match_found:
    # Trigger orchestrator agent
    agent = OrchestratorAgent(...)
    results = agent.run_research_pipeline(
        company=company,
        topics=query_intent.topics
    )
    return results
```

## Dependencies

```bash
# Core NLP
pip install spacy
python -m spacy download en_core_web_sm

# Embeddings
pip install sentence-transformers

# Already installed
# - google-generativeai (for Gemini)
# - textblob
# - scikit-learn (for cosine_similarity)
# - numpy
```

## Troubleshooting

### "spaCy model not found"
```bash
python -m spacy download en_core_web_sm
```

### "Intelligent Query Router not available"
Check logs for specific error. Common issues:
- Missing `GEMINI_API_KEY`
- Import errors (missing dependencies)
- Supabase connection issues

### "No topics found for company"
Possible causes:
- Company not in database
- Ticker/name mismatch (check `companies` table)
- Database connection issue

### Low cache hit rate
Adjust similarity threshold lower (e.g., 0.65-0.70) or:
- Check topic descriptions (more detailed = better matching)
- Verify embeddings are being generated
- Review query analysis quality

## Testing

See `test_intelligent_query.py` for comprehensive tests.

## Future Enhancements

1. **Pre-compute topic embeddings** (store in database)
2. **Multi-company queries** (e.g., "Apple vs Samsung")
3. **Time-aware matching** (prefer recent topics)
4. **User feedback loop** (learn from clicks)
5. **Query expansion** (add synonyms)
6. **Hybrid search** (combine semantic + keyword)
