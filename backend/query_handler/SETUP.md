# Intelligent Query System - Setup Guide

## Quick Setup

### 1. Install Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate

# Install spaCy and download English model
pip install spacy
python -m spacy download en_core_web_sm

# sentence-transformers already installed (from requirements-dev.txt)
```

### 2. Environment Variables

Add to your `.env` file:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Required for database features
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_or_service_key
```

### 3. Test the System

```bash
# Run the test suite
cd backend
python query_handler/test_intelligent_query.py
```

Expected output:
```
✅ PASS - Query Analyzer
✅ PASS - Topic Matcher
✅ PASS - Full Routing
✅ PASS - Performance

Total: 4/4 tests passed
```

### 4. Integration with Backend

The system is automatically integrated into your FastAPI backend via [article_retriever_router.py](article_retriever_router.py:73-91).

It initializes on startup if:
- `GEMINI_API_KEY` is set
- `hybrid_query_analyzer.py` and `intelligent_query_router.py` are available

Check logs for:
```
✅ Intelligent Query Router initialized
```

## Usage

### API Endpoint

The intelligent query system is available at:

```
GET /api/articles/search?q={user_query}
```

### Example Requests

**1. Natural language query:**
```bash
curl "http://localhost:8004/api/articles/search?q=What's happening with Tesla earnings?"
```

**2. Product-specific query:**
```bash
curl "http://localhost:8004/api/articles/search?q=Apple Vision Pro sales numbers"
```

**3. General company query:**
```bash
curl "http://localhost:8004/api/articles/search?q=Microsoft cloud revenue"
```

### Response Types

**Cache Hit (articles found in database):**
```json
[
  {
    "id": "abc123",
    "title": "Tesla Q4 Earnings Beat Expectations",
    "source": "Bloomberg",
    "url": "https://...",
    "cached": true,
    "relevance_score": 0.92
  }
]
```

**Fresh Search Needed:**
```json
{
  "status": "fresh_search_needed",
  "message": "No cached research found",
  "query_intent": {
    "companies": ["Tesla"],
    "tickers": ["TSLA"],
    "topics": ["earnings"]
  },
  "search_params": {
    "company": "TSLA",
    "topics": ["earnings", "Q4"]
  },
  "articles": [ /* fallback articles */ ]
}
```

## How It Works

### Query Flow

1. **User submits query** → `/api/articles/search?q=Tesla earnings`

2. **Hybrid extraction** (70ms average):
   - Regex: Finds "TSLA" if present
   - spaCy: Identifies "Tesla" as organization
   - TextBlob: Extracts "earnings" keyword
   - Gemini: Only if confidence < 0.7

3. **Database lookup**:
   - Finds company "Tesla" (or "TSLA") in database
   - Retrieves existing topics for Tesla

4. **Topic matching** (100ms first time, 1ms cached):
   - Generates embeddings for query topics
   - Compares to existing topic embeddings
   - Returns match if similarity > 0.75

5. **Result**:
   - ✅ **Match found**: Return cached articles (fast!)
   - ❌ **No match**: Indicate fresh search needed

### Database Schema Compatibility

The system handles your current schema:

✅ **Ticker in `name` column**: Queries use `name` for lookups
✅ **No topic embeddings**: Generates on-demand and caches
✅ **Multiple companies**: Supports company name or ticker

### Fallback Strategy

When no good match is found (similarity < 0.75):

```python
{
    'source': 'fresh_search',
    'search_params': {
        'company': 'Tesla',
        'topics': ['earnings', 'Q4'],
        'keywords': ['financial', 'results']
    }
}
```

Your application can then:
1. Trigger `OrchestratorAgent` with these params
2. Store results in database
3. Return to user

## Configuration

### Similarity Threshold

Adjust in [intelligent_query_router.py](intelligent_query_router.py:242):

```python
matched_topic = self.topic_matcher.match_query_to_topics(
    threshold=0.75  # ← Change this value
)
```

**Recommendations:**
- **0.85**: Strict (fewer cache hits, more accuracy)
- **0.75**: Balanced (default)
- **0.65**: Loose (more cache hits, some false positives)

### LLM Fallback Threshold

Adjust in [hybrid_query_analyzer.py](hybrid_query_analyzer.py:127):

```python
if result['confidence'] < 0.7:  # ← Change threshold
    llm_result = self._extract_with_llm(query)
```

Lower = use LLM more often (higher cost, better accuracy)
Higher = use LLM less often (lower cost, may miss complex queries)

## Troubleshooting

### "spaCy model not found"

```bash
python -m spacy download en_core_web_sm
```

### "Intelligent Query Router not available"

Check backend logs for specific error. Common causes:
- Missing `GEMINI_API_KEY`
- Import errors
- Supabase connection issues

### No results returned

1. Check if company exists in database:
```python
# In python shell
from deep_news_agent.db.research_db_manager import ResearchDBManager
db = ResearchDBManager(supabase_url, supabase_key)
topics = db.get_company_topics("Tesla")
print(f"Found {len(topics)} topics")
```

2. Check logs for similarity scores:
```
Topic 'Q4 Earnings' similarity: 0.82 ✅
Topic 'Product Launch' similarity: 0.45 ❌
```

3. Lower threshold temporarily to test:
```python
matched_topic = matcher.match_query_to_topics(
    threshold=0.5  # Temporary - for testing
)
```

### Performance issues

**Slow first query:**
- Normal! Embeddings are generated on first access
- Subsequent queries will be fast (cached)

**All queries slow:**
- Check if Gemini LLM is being called too often
- Review confidence scores in logs
- Consider raising LLM threshold

## Monitoring

### Key Metrics to Track

1. **Cache hit rate**: `source == 'cache'` responses
2. **LLM usage rate**: Check logs for "using LLM fallback"
3. **Average response time**: Fast path should be < 200ms
4. **Similarity scores**: Log all matches to tune threshold

### Example Logging

Add to your backend:

```python
# Log query performance
logger.info(f"Query: {query}")
logger.info(f"Cache: {'HIT' if cached else 'MISS'}")
logger.info(f"Response time: {elapsed_ms}ms")
logger.info(f"Articles returned: {len(articles)}")
```

## Next Steps

1. **Run tests**: `python query_handler/test_intelligent_query.py`
2. **Try queries**: Test with your actual data
3. **Monitor performance**: Check cache hit rates
4. **Tune thresholds**: Adjust based on your needs
5. **Implement fresh search**: Handle `fresh_search_needed` responses

## Support

See [INTELLIGENT_QUERY_SYSTEM.md](INTELLIGENT_QUERY_SYSTEM.md) for detailed documentation.

For issues:
- Check logs for error messages
- Review test output
- Verify environment variables
- Ensure database has data
