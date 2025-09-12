-- Supabase Database Schema for News Aggregator
-- Run this SQL in your Supabase SQL editor to set up the required tables and functions

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create content_chunks table
CREATE TABLE IF NOT EXISTS content_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    processed_content TEXT,
    embedding vector(384),
    metadata JSONB NOT NULL,
    cluster_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create content_clusters table
CREATE TABLE IF NOT EXISTS content_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    centroid vector(384),
    metadata JSONB NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create cluster_summaries table
CREATE TABLE IF NOT EXISTS cluster_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES content_clusters(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    key_points JSONB,
    metadata JSONB,
    generated_at TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR(100),
    confidence FLOAT DEFAULT 1.0,
    word_count INTEGER DEFAULT 0
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON content_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_clusters_centroid ON content_clusters 
USING ivfflat (centroid vector_cosine_ops)
WITH (lists = 100);

-- Create other useful indexes
CREATE INDEX IF NOT EXISTS idx_chunks_cluster_id ON content_chunks(cluster_id);
CREATE INDEX IF NOT EXISTS idx_chunks_created_at ON content_chunks(created_at);
CREATE INDEX IF NOT EXISTS idx_clusters_created_at ON content_clusters(created_at);
CREATE INDEX IF NOT EXISTS idx_summaries_cluster_id ON cluster_summaries(cluster_id);

-- Create metadata indexes for common queries
CREATE INDEX IF NOT EXISTS idx_chunks_metadata_ticker ON content_chunks 
USING GIN ((metadata->>'ticker'));
CREATE INDEX IF NOT EXISTS idx_chunks_metadata_topic ON content_chunks 
USING GIN ((metadata->>'topic'));
CREATE INDEX IF NOT EXISTS idx_chunks_metadata_source ON content_chunks 
USING GIN ((metadata->>'source'));

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION match_chunks (
    query_embedding vector(384),
    similarity_threshold float DEFAULT 0.8,
    match_count int DEFAULT 10,
    exclude_ids uuid[] DEFAULT '{}'
)
RETURNS TABLE (
    id uuid,
    content text,
    processed_content text,
    metadata jsonb,
    cluster_id uuid,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        content_chunks.id,
        content_chunks.content,
        content_chunks.processed_content,
        content_chunks.metadata,
        content_chunks.cluster_id,
        1 - (content_chunks.embedding <=> query_embedding) as similarity
    FROM content_chunks
    WHERE content_chunks.embedding IS NOT NULL
    AND content_chunks.id <> ALL(exclude_ids)
    AND 1 - (content_chunks.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY content_chunks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to get recent chunks (for duplicate checking)
CREATE OR REPLACE FUNCTION get_recent_chunks (
    hours_back int DEFAULT 24,
    limit_count int DEFAULT 100
)
RETURNS TABLE (
    id uuid,
    content text,
    processed_content text,
    embedding vector(384),
    metadata jsonb,
    cluster_id uuid,
    created_at timestamp
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        content_chunks.id,
        content_chunks.content,
        content_chunks.processed_content,
        content_chunks.embedding,
        content_chunks.metadata,
        content_chunks.cluster_id,
        content_chunks.created_at
    FROM content_chunks
    WHERE content_chunks.created_at > NOW() - INTERVAL '1 hour' * hours_back
    AND content_chunks.embedding IS NOT NULL
    ORDER BY content_chunks.created_at DESC
    LIMIT limit_count;
END;
$$;

-- Function to find similar clusters
CREATE OR REPLACE FUNCTION match_clusters (
    query_embedding vector(384),
    similarity_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    centroid vector(384),
    metadata jsonb,
    chunk_count integer,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        content_clusters.id,
        content_clusters.centroid,
        content_clusters.metadata,
        content_clusters.chunk_count,
        1 - (content_clusters.centroid <=> query_embedding) as similarity
    FROM content_clusters
    WHERE content_clusters.centroid IS NOT NULL
    AND 1 - (content_clusters.centroid <=> query_embedding) >= similarity_threshold
    ORDER BY content_clusters.centroid <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data (
    days_to_keep int DEFAULT 30
)
RETURNS TABLE (
    chunks_deleted bigint,
    clusters_deleted bigint
)
LANGUAGE plpgsql
AS $$
DECLARE
    chunks_count bigint;
    clusters_count bigint;
BEGIN
    -- Delete old chunks
    DELETE FROM content_chunks 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    GET DIAGNOSTICS chunks_count = ROW_COUNT;
    
    -- Delete old clusters (cascades to summaries)
    DELETE FROM content_clusters 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    GET DIAGNOSTICS clusters_count = ROW_COUNT;
    
    RETURN QUERY SELECT chunks_count, clusters_count;
END;
$$;

-- Enable Row Level Security (optional - for production)
-- ALTER TABLE content_chunks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE content_clusters ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cluster_summaries ENABLE ROW LEVEL SECURITY;

-- Create policies if RLS is enabled (uncomment if needed)
-- CREATE POLICY "Enable all operations for authenticated users" ON content_chunks
-- FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- CREATE POLICY "Enable all operations for authenticated users" ON content_clusters
-- FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- CREATE POLICY "Enable all operations for authenticated users" ON cluster_summaries
-- FOR ALL TO authenticated USING (true) WITH CHECK (true);
