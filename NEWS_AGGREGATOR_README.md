# News Aggregator System

A comprehensive news aggregation system that processes content from multiple sources, removes duplicates, creates semantic clusters, and generates AI-powered summaries using Google's Gemini API.

## Architecture Overview

```mermaid
graph TD
    A[PlannerAgent Results] --> B[TextPreprocessor]
    B --> C[EmbeddingManager]
    C --> D[DeduplicationEngine]
    D --> E[ClusteringEngine]
    E --> F[ClusterScorer]
    F --> G[GeminiSummarizer]
    G --> H[DatabaseManager]
    H --> I[Structured Output]
    
    J[RealtimeProcessor] --> B
    K[EnhancedPlannerAgent] --> A
```

## Core Components

### 1. **AggregatorAgent** - Main Orchestrator
The primary class that coordinates the entire aggregation pipeline:
- Processes raw content from retrievers
- Manages the complete workflow
- Provides both sync and async interfaces
- Handles error recovery and fallbacks

### 2. **TextPreprocessor** - Content Cleaning
Handles text preprocessing and normalization:
- HTML tag removal and text extraction
- Boilerplate content detection and removal
- Language detection and filtering
- Source type classification
- Content chunking for large texts

### 3. **EmbeddingManager** - Semantic Embeddings
Manages sentence embeddings using SentenceTransformers:
- Uses `all-MiniLM-L6-v2` model by default (384 dimensions)
- Batch processing for efficiency
- Embedding caching system
- Similarity calculations and vector operations

### 4. **DeduplicationEngine** - Duplicate Removal
Multi-layered deduplication system:
- Exact URL matching
- Title-based fuzzy matching
- Content hash deduplication
- Semantic similarity using embeddings
- Quality-based duplicate resolution

### 5. **ClusteringEngine** - Semantic Clustering
HDBSCAN-based clustering of related content:
- Density-based semantic clustering
- Dynamic cluster management
- Real-time cluster updates
- Cluster quality assessment

### 6. **ClusterScorer** - Multi-factor Scoring
Comprehensive scoring system based on:
- **Recency**: Time-based decay (40% weight)
- **Reliability**: Source quality tiers (35% weight)  
- **Relevance**: User preference matching (25% weight)
- **Breaking News**: Automatic detection and boosting
- **Source Diversity**: Bonus for multiple sources

### 7. **GeminiSummarizer** - AI Summarization
Google Gemini API integration:
- Structured summary generation
- Key point extraction
- Batch processing support
- Fallback summaries for failures

### 8. **DatabaseManager** - pgvector Storage
PostgreSQL with pgvector extension:
- Vector similarity search
- Chunk and cluster storage
- Summary management
- Efficient indexing strategies

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL with pgvector extension
- Google Gemini API key
- Supabase account (optional)

### Dependencies
```bash
pip install sentence-transformers hdbscan scikit-learn google-generativeai \
           fuzzywuzzy psycopg2-binary asyncpg sqlalchemy beautifulsoup4 \
           langdetect numpy pandas
```

### Database Setup
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- The system will automatically create tables on first run
```

## Quick Start

### Basic Usage
```python
from news_agent.aggregator import create_aggregator_agent

# Create aggregator with API key
aggregator = create_aggregator_agent(
    gemini_api_key="your-gemini-api-key",
    database_url="postgresql://user:pass@host:5432/dbname"
)

# Process PlannerAgent results
planner_results = {
    "breaking_news": [...],
    "financial_news": [...],
    "sec_filings": [...],
    "general_news": [...]
}

# Run aggregation
output = aggregator.process_planner_results(
    planner_results=planner_results,
    user_preferences={
        'watchlist': ['AAPL', 'GOOGL', 'MSFT'],
        'topics': ['technology', 'ai'],
        'keywords': ['earnings', 'revenue']
    }
)

# Access results
for cluster in output.clusters:
    print(f"Cluster: {cluster.chunk_count} articles")
    print(f"Summary: {cluster.summary.summary}")
    print(f"Sources: {cluster.source_count}")
```

### Enhanced PlannerAgent Integration
```python
from news_agent.integration import create_enhanced_planner

# Create enhanced planner with aggregation
planner = create_enhanced_planner(
    gemini_api_key="your-api-key",
    database_url="postgresql://...",
    max_retrievers=5
)

# Run enhanced search
results = await planner.run_async(
    query="Apple earnings AI technology",
    user_preferences={'watchlist': ['AAPL']},
    return_aggregated=True
)

# Access both raw and aggregated results
raw_articles = results['breaking_news']  # Raw PlannerAgent results
summaries = results['summaries']  # AI-generated cluster summaries
clusters = results['aggregation']['clusters']  # Full cluster data
```

### Real-time Processing
```python
from news_agent.integration import create_realtime_processor

# Create real-time processor
processor = create_realtime_processor(
    aggregator=aggregator,
    config_overrides={
        'batch_size': 25,
        'batch_interval': 15,
        'num_workers': 3
    }
)

# Start processing
processor.start()

# Submit jobs
def result_callback(job_id, result):
    print(f"Job {job_id}: {len(result.clusters)} clusters created")

job_id = processor.submit_planner_results(
    planner_results=planner_results,
    priority=2,  # Higher priority
    callback=result_callback
)

# Monitor status
status = processor.get_status()
print(f"Queue size: {status['queue_size']}")
print(f"Active clusters: {status['active_clusters']}")
```

## Configuration

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
BATCH_SIZE=50
BATCH_INTERVAL=30
MIN_CLUSTER_SIZE=3
SIMILARITY_THRESHOLD=0.8
RECENCY_WEIGHT=0.4
RELIABILITY_WEIGHT=0.35
RELEVANCE_WEIGHT=0.25
```

### Configuration File
```python
from news_agent.aggregator import AggregatorConfig

config = AggregatorConfig()

# Embedding settings
config.embedding.model_name = "sentence-transformers/all-MiniLM-L6-v2"
config.embedding.batch_size = 32

# Clustering settings
config.clustering.min_cluster_size = 3
config.clustering.similarity_threshold = 0.8

# Scoring weights
config.scoring.recency_weight = 0.4
config.scoring.reliability_weight = 0.35
config.scoring.relevance_weight = 0.25

# Summarization settings
config.summarizer.model_name = "gemini-1.5-flash"
config.summarizer.temperature = 0.3
config.summarizer.max_output_tokens = 500
```

## Output Format

### Cluster Summary Structure
```json
{
  "id": "cluster_uuid",
  "summary": "AI-generated summary of the cluster",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3"
  ],
  "sources": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "author": "Author Name",
      "timestamp": "2024-01-01T10:00:00Z",
      "excerpt": "Key excerpt from article",
      "relevance_score": 0.95
    }
  ],
  "metadata": {
    "ticker": "AAPL",
    "topics": ["earnings", "technology"],
    "source_count": 5,
    "cluster_size": 8,
    "confidence_score": 0.87,
    "cluster_score": 0.92
  }
}
```

### Processing Statistics
```json
{
  "processing_time_seconds": 2.45,
  "total_clusters": 6,
  "total_sources": 25,
  "total_chunks_processed": 45,
  "deduplication": {
    "original_count": 45,
    "deduplicated_count": 38,
    "removal_percentage": 15.6
  },
  "clustering": {
    "num_clusters": 6,
    "average_cluster_size": 6.3,
    "silhouette_score": 0.72
  }
}
```

## Source Reliability Tiers

The system classifies sources into reliability tiers:

- **Tier 1 (Score: 1.0)**: Official sources (SEC.gov, Treasury.gov, etc.)
- **Tier 2 (Score: 0.9)**: Major news agencies (Reuters, Bloomberg, AP)
- **Tier 3 (Score: 0.8)**: Established media (CNN, CNBC, WSJ, NYT)
- **Tier 4 (Score: 0.6)**: Smaller outlets (Yahoo, Business Insider)
- **Tier 5 (Score: 0.4)**: Blogs, social media, unverified sources

## User Preferences

### Supported Preference Types

```python
user_preferences = {
    'watchlist': ['AAPL', 'GOOGL', 'MSFT'],  # Stock tickers
    'topics': ['technology', 'finance', 'ai'],  # Topics of interest
    'keywords': ['earnings', 'revenue', 'innovation'],  # Keywords
    'sectors': ['technology', 'healthcare', 'finance']  # Industry sectors
}
```

## Performance Optimization

### Batch Processing
- Process multiple items together for efficiency
- Configurable batch sizes and intervals
- Automatic batching in real-time processor

### Caching
- Embedding cache to avoid recomputation
- Recent chunks cache for duplicate detection
- Database connection pooling

### Async Processing
- Full async support throughout the pipeline
- Concurrent embedding generation
- Parallel summary generation

## Monitoring and Logging

### Built-in Monitoring
```python
# Get performance stats
stats = aggregator.get_performance_stats()
print(f"Average processing time: {stats['avg_processing_time']:.2f}s")
print(f"Total processed: {stats['total_chunks_processed']}")

# Real-time processor monitoring
from news_agent.integration.realtime_processor import ProcessorMonitor

monitor = ProcessorMonitor(processor)
monitor.print_status()
```

### Logging Configuration
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('news_agent.aggregator')
logger.setLevel(logging.DEBUG)
```

## Error Handling

The system includes comprehensive error handling:

- **Graceful Degradation**: Falls back to simpler methods if advanced features fail
- **Retry Logic**: Automatic retries for API calls and database operations
- **Fallback Summaries**: Basic summaries when AI generation fails
- **Error Recovery**: Continues processing even when individual components fail

## Testing

### Unit Tests
```bash
# Run aggregator tests
python -m pytest tests/test_aggregator.py

# Run integration tests
python -m pytest tests/test_integration.py
```

### Manual Testing
```python
# Test individual components
from news_agent.aggregator import TextPreprocessor, EmbeddingManager

preprocessor = TextPreprocessor(config.preprocessing)
chunks = preprocessor.process_planner_results(test_data)

embedding_manager = EmbeddingManager(config.embedding)
embedded_chunks = embedding_manager.embed_chunks(chunks)
```

## API Reference

### Core Classes

#### AggregatorAgent
- `process_planner_results(planner_results, user_preferences=None) -> AggregatorOutput`
- `process_planner_results_async(planner_results, user_preferences=None) -> AggregatorOutput`
- `get_performance_stats() -> Dict[str, Any]`
- `cleanup()`

#### EnhancedPlannerAgent
- `run_async(query, user_preferences=None, return_aggregated=True) -> Dict[str, Any]`
- `run(query, user_preferences=None, return_aggregated=True) -> Dict[str, Any]`
- `get_aggregator_stats() -> Dict[str, Any]`

#### RealtimeProcessor
- `start()`
- `stop()`
- `submit_job(content, priority=1, user_preferences=None, callback=None) -> str`
- `get_status() -> Dict[str, Any]`
- `register_callback(event_type, callback)`

## Troubleshooting

### Common Issues

1. **Gemini API Errors**
   - Ensure valid API key is set
   - Check API quota limits
   - Verify model name is correct

2. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Ensure pgvector extension is installed
   - Check connection string format

3. **Memory Issues**
   - Reduce batch sizes for large datasets
   - Enable embedding caching
   - Monitor cluster count limits

4. **Slow Performance**
   - Enable GPU for embedding generation
   - Increase worker threads for real-time processing
   - Optimize database indexes

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger('news_agent.aggregator').setLevel(logging.DEBUG)

# Use smaller batch sizes for testing
config = AggregatorConfig()
config.processing.max_batch_size = 10
config.embedding.batch_size = 8
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.
