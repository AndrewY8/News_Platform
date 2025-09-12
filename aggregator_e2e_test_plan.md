# End-to-End Test Plan for News Aggregator

## Overview
This document outlines the comprehensive end-to-end testing strategy for the News Aggregator system, covering the complete pipeline from PlannerAgent results to final summarized clusters.

## Test Architecture

### 1. Test Scenarios
The test will cover multiple realistic scenarios:

#### Scenario A: Breaking News Technology
- **Content**: 3-4 articles about a major tech announcement (Apple M4 Ultra chip)
- **Expected**: 1 cluster with high breaking news score
- **Sources**: TechCrunch, ArsTechnica, Bloomberg, Reuters
- **Validation**: Cluster coherence, summary quality, breaking news detection

#### Scenario B: Financial Earnings Reports
- **Content**: Multiple earnings reports from different companies
- **Expected**: 2-3 clusters grouped by company/sector
- **Sources**: Bloomberg, MarketWatch, SEC filings
- **Validation**: Ticker extraction, financial source reliability, clustering accuracy

#### Scenario C: Mixed General News
- **Content**: Diverse topics (politics, sports, science, business)
- **Expected**: 3-5 distinct clusters
- **Sources**: CNN, BBC, Washington Post, Scientific American
- **Validation**: Topic separation, source diversity bonus, relevance scoring

#### Scenario D: Duplicate Content Detection
- **Content**: Same story from multiple sources with slight variations
- **Expected**: 1 cluster with proper deduplication
- **Sources**: Multiple outlets covering the same event
- **Validation**: Deduplication effectiveness, quality-based source selection

### 2. Test Components

#### Core Pipeline Tests
1. **Initialization Tests**
   - Configuration validation
   - Component initialization
   - API key validation
   - Error handling for missing dependencies

2. **Preprocessing Tests**
   - HTML cleaning
   - Content normalization
   - Language detection
   - Ticker extraction
   - Source classification

3. **Embedding Generation Tests**
   - Batch processing efficiency
   - Cache utilization
   - Embedding quality validation
   - Error handling for failed embeddings

4. **Deduplication Tests**
   - URL-based deduplication
   - Title similarity matching
   - Content hash deduplication
   - Semantic similarity deduplication
   - Quality-based duplicate resolution

5. **Clustering Tests**
   - Semantic clustering accuracy
   - Cluster size validation
   - Centroid calculation
   - Cluster metadata generation
   - Cluster coherence scoring

6. **Scoring Tests**
   - Recency scoring with time decay
   - Source reliability weighting
   - User preference matching
   - Breaking news detection and boosting
   - Source diversity bonuses

7. **Summarization Tests**
   - Gemini API integration
   - Summary generation quality
   - Key point extraction
   - Batch processing efficiency
   - Error handling and fallback summaries

#### Integration Tests
1. **Synchronous Pipeline Test**
   - Full pipeline execution
   - Performance measurement
   - Memory usage tracking
   - Error propagation handling

2. **Asynchronous Pipeline Test**
   - Async processing efficiency
   - Concurrent task management
   - Resource utilization
   - Error isolation

3. **Incremental Processing Test**
   - New content addition
   - Existing cluster updates
   - Cluster merging/splitting
   - Performance with growing dataset

#### Validation Tests
1. **Output Format Validation**
   - AggregatorOutput structure
   - ContentCluster format
   - ClusterSummary format
   - JSON serialization compatibility

2. **Content Quality Validation**
   - Summary coherence and relevance
   - Key point accuracy
   - Source attribution correctness
   - Metadata completeness

3. **Performance Validation**
   - Processing time benchmarks
   - Memory usage limits
   - API rate limit handling
   - Scalability testing

#### Error Handling Tests
1. **Input Validation**
   - Empty/invalid planner results
   - Malformed content chunks
   - Missing required fields
   - Invalid configuration parameters

2. **Component Failure Handling**
   - Embedding generation failures
   - Clustering algorithm failures
   - Summarization API failures
   - Database connection failures

3. **Resource Limit Handling**
   - Memory constraints
   - API rate limits
   - Token limits for summarization
   - Timeout handling

## Mock Data Structure

### Mock PlannerAgent Results Format
```python
{
    "breaking_news": [
        {
            "title": "Article Title",
            "url": "https://example.com/article",
            "description": "Brief description",
            "raw_content": "Full article content...",
            "source_retriever": "TavilyRetriever",
            "published_date": "2024-01-15T10:30:00Z",
            "author": "Author Name",
            "image_urls": ["https://example.com/image.jpg"]
        }
    ],
    "financial_news": [...],
    "general_news": [...],
    "sec_filings": [...]
}
```

## Test Execution Strategy

### 1. Environment Setup
- Validate Gemini API key availability
- Check required dependencies
- Configure logging and reporting
- Set up test data directories

### 2. Sequential Test Execution
1. Configuration and initialization tests
2. Individual component tests
3. Integration pipeline tests
4. Performance and scalability tests
5. Error handling and edge cases

### 3. Result Validation
- Automated assertions for expected outcomes
- Manual review points for subjective quality
- Performance benchmark comparisons
- Statistical analysis of results

### 4. Comprehensive Reporting
- Test execution summary
- Performance metrics
- Quality assessments
- Failure analysis
- Recommendations for improvements

## Success Criteria

### Functional Requirements
- ✅ All test scenarios process without critical errors
- ✅ Clustering accuracy >= 80% (manually verified)
- ✅ Deduplication effectiveness >= 85%
- ✅ Summary quality meets subjective standards
- ✅ Output format compliance 100%

### Performance Requirements
- ✅ Processing time < 60 seconds for 50 articles
- ✅ Memory usage < 2GB for standard test datasets
- ✅ API rate limits respected (no 429 errors)
- ✅ Async processing shows improvement over sync

### Quality Requirements
- ✅ Generated summaries are coherent and factual
- ✅ Key points accurately reflect article content
- ✅ Source attribution is correct
- ✅ Cluster metadata is comprehensive

## Implementation Notes

### Test File Structure
```
test_aggregator_e2e.py
├── AggregatorE2ETester (main class)
├── Test scenarios and mock data
├── Individual component tests
├── Integration pipeline tests
├── Validation and quality checks
├── Performance measurement
├── Error handling tests
└── Comprehensive reporting
```

### Dependencies
- All aggregator components
- Gemini API access
- Test data generators
- Performance monitoring tools
- Report generation utilities

### Integration with Existing Test Suite
- Follow existing test patterns from test_integration.py
- Use similar reporting format as run_tests.py
- Integrate with master test runner
- Generate JSON results for automation

This comprehensive test plan ensures thorough validation of the News Aggregator system across all dimensions: functionality, performance, quality, and reliability.
