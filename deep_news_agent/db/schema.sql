-- News_DB Schema for Research Orchestrator Pipeline
-- Designed to work with existing topic extraction and ranking pipeline

-- Companies table
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    ticker VARCHAR(10),
    business_areas JSONB, -- Store as JSON array: ["Consumer Electronics", "Software Services"]
    current_status JSONB, -- Store company context data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Topics table (stores extracted topics from pipeline)
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,

    -- Core topic data (from TopicAgent extraction)
    name VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    business_impact TEXT NOT NULL,
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    urgency VARCHAR(20) NOT NULL CHECK (urgency IN ('high', 'medium', 'low')),

    -- Pipeline metadata
    extraction_date TIMESTAMP DEFAULT NOW(),
    pipeline_iteration INTEGER, -- Which iteration discovered this topic

    -- Ranking scores (from RankingAgent)
    final_score DECIMAL(5,4),
    impact_score DECIMAL(5,4),
    recency_score DECIMAL(5,4),
    relatedness_score DECIMAL(5,4),
    credibility_score DECIMAL(5,4),
    rank_position INTEGER,

    -- Subtopics as JSON for now (since they're just metadata)
    subtopics JSONB, -- ["AI Infrastructure", "On-device Processing"]

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Articles table (stores search results that contributed to topic extraction)
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,

    -- Article content
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    summary TEXT, -- Can store excerpt or AI-generated summary

    -- Source metadata
    source VARCHAR(100) NOT NULL, -- "tavily", "earnings_transcript", "trusted_news", etc.
    source_domain VARCHAR(255), -- "bloomberg.com", "reuters.com", etc.
    published_date TIMESTAMP,

    -- Search metadata
    search_query TEXT, -- Which query found this article
    relevance_score DECIMAL(3,2), -- From search API
    pipeline_iteration INTEGER, -- Which iteration found this

    -- Embeddings (keep your existing functionality)
    embedding VECTOR(384),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Junction table: Many-to-many relationship between articles and topics
CREATE TABLE article_topics (
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,

    -- Relationship metadata
    contribution_strength DECIMAL(3,2) DEFAULT 0.5, -- How much this article contributed to this topic
    extraction_method VARCHAR(50) DEFAULT 'batch_extraction', -- How the link was determined

    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (article_id, topic_id)
);

-- Indexes for performance
CREATE INDEX idx_topics_company_id ON topics(company_id);
CREATE INDEX idx_topics_final_score ON topics(final_score DESC);
CREATE INDEX idx_topics_extraction_date ON topics(extraction_date DESC);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_published_date ON articles(published_date DESC);
CREATE INDEX idx_article_topics_topic_id ON article_topics(topic_id);
CREATE INDEX idx_article_topics_article_id ON article_topics(article_id);

-- Enhanced indexes for subtopic functionality
CREATE INDEX idx_topics_subtopics_gin ON topics USING GIN (subtopics);
CREATE INDEX idx_topics_urgency ON topics(urgency);
CREATE INDEX idx_topics_confidence ON topics(confidence DESC);

-- Views for common queries
CREATE VIEW company_topic_summary AS
SELECT
    c.name as company_name,
    c.ticker,
    COUNT(t.id) as total_topics,
    COUNT(CASE WHEN t.urgency = 'high' THEN 1 END) as high_urgency_topics,
    AVG(t.final_score) as avg_topic_score,
    MAX(t.extraction_date) as last_research_date
FROM companies c
LEFT JOIN topics t ON c.id = t.company_id
GROUP BY c.id, c.name, c.ticker;

CREATE VIEW topic_article_summary AS
SELECT
    t.id as topic_id,
    t.name as topic_name,
    t.company_id,
    COUNT(at.article_id) as article_count,
    ARRAY_AGG(DISTINCT a.source) as sources_used,
    AVG(a.relevance_score) as avg_article_relevance
FROM topics t
LEFT JOIN article_topics at ON t.id = at.topic_id
LEFT JOIN articles a ON at.article_id = a.id
GROUP BY t.id, t.name, t.company_id;

-- Enhanced views for subtopic analysis
CREATE VIEW topic_with_subtopics AS
SELECT
    t.id as topic_id,
    t.name as topic_name,
    t.company_id,
    t.urgency,
    t.confidence,
    t.final_score,
    t.extraction_date,
    CASE
        WHEN t.subtopics IS NOT NULL AND jsonb_array_length(t.subtopics) > 0
        THEN jsonb_array_length(t.subtopics)
        ELSE 0
    END as subtopic_count,
    t.subtopics
FROM topics t;

CREATE VIEW subtopic_detail AS
SELECT
    t.id as topic_id,
    t.name as topic_name,
    t.company_id,
    subtopic_data->>'name' as subtopic_name,
    (subtopic_data->>'confidence')::decimal(3,2) as subtopic_confidence,
    subtopic_data->'sources' as subtopic_sources,
    subtopic_data->'article_indices' as subtopic_article_indices,
    subtopic_data->>'extraction_method' as subtopic_extraction_method
FROM topics t,
LATERAL jsonb_array_elements(COALESCE(t.subtopics, '[]'::jsonb)) as subtopic_data
WHERE t.subtopics IS NOT NULL AND jsonb_array_length(t.subtopics) > 0;

CREATE VIEW company_subtopic_analysis AS
SELECT
    c.name as company_name,
    c.ticker,
    COUNT(DISTINCT t.id) as topics_with_subtopics,
    COUNT(sd.subtopic_name) as total_subtopics,
    ROUND(AVG(sd.subtopic_confidence), 3) as avg_subtopic_confidence,
    ARRAY_AGG(DISTINCT sd.subtopic_extraction_method) as extraction_methods_used
FROM companies c
LEFT JOIN topics t ON c.id = t.company_id
LEFT JOIN subtopic_detail sd ON t.id = sd.topic_id
WHERE t.subtopics IS NOT NULL AND jsonb_array_length(t.subtopics) > 0
GROUP BY c.id, c.name, c.ticker;

-- PostgreSQL function for searching subtopics by name pattern
CREATE OR REPLACE FUNCTION search_subtopics_by_name(
    company_name_param TEXT,
    name_pattern TEXT
)
RETURNS TABLE (
    topic_id INTEGER,
    topic_name VARCHAR(500),
    subtopic_name TEXT,
    subtopic_confidence DECIMAL(3,2),
    subtopic_sources JSONB,
    subtopic_article_indices JSONB,
    subtopic_extraction_method TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sd.topic_id,
        sd.topic_name,
        sd.subtopic_name,
        sd.subtopic_confidence,
        sd.subtopic_sources,
        sd.subtopic_article_indices,
        sd.subtopic_extraction_method
    FROM subtopic_detail sd
    JOIN topics t ON sd.topic_id = t.id
    JOIN companies c ON t.company_id = c.id
    WHERE c.name = company_name_param
    AND sd.subtopic_name ILIKE '%' || name_pattern || '%';
END;
$$;