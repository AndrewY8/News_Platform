"""
Supabase manager for news aggregator system.

This module provides database operations using Supabase REST API
instead of direct PostgreSQL connections, eliminating the need
for database passwords and connection strings.
"""

import logging
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from .models import ContentChunk, ContentCluster, ClusterSummary

logger = logging.getLogger(__name__)


class SupabaseManager:
    """
    Manages database operations using Supabase REST API.
    
    Features:
    - REST API based operations (no direct PostgreSQL connection)
    - Vector similarity search through database functions
    - CRUD operations for chunks, clusters, and summaries
    - Built-in connection pooling and retry logic
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, vector_dimension: int = 384):
        """
        Initialize Supabase manager.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (anon or service role)
            vector_dimension: Vector dimension for embeddings
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase-py is required for Supabase operations. Install with: pip install supabase")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Both supabase_url and supabase_key are required")
        
        self.client: Client = create_client(supabase_url, supabase_key)
        self.vector_dimension = vector_dimension
        
        logger.info("SupabaseManager initialized successfully")
    
    def create_schema(self):
        """
        Create database schema with pgvector extension and tables.
        Note: This should be run once through Supabase SQL editor or migration.
        """
        schema_sql = f"""
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Create content_chunks table
        CREATE TABLE IF NOT EXISTS content_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            processed_content TEXT,
            embedding vector({self.vector_dimension}),
            metadata JSONB NOT NULL,
            cluster_id UUID,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Create content_clusters table
        CREATE TABLE IF NOT EXISTS content_clusters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            centroid vector({self.vector_dimension}),
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
            query_embedding vector({self.vector_dimension}),
            similarity_threshold float DEFAULT 0.8,
            match_count int DEFAULT 10,
            exclude_ids uuid[] DEFAULT '{{}}'
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
        """
        
        logger.warning("Schema creation should be run through Supabase SQL editor:")
        logger.warning("Copy the following SQL to your Supabase project:")
        logger.warning(schema_sql)
        
        # For now, we can't execute raw SQL through the REST API
        # This would need to be run manually in Supabase SQL editor
    
    def insert_chunk(self, chunk: ContentChunk) -> str:
        """
        Insert a content chunk into the database.
        
        Args:
            chunk: ContentChunk to insert
            
        Returns:
            ID of the inserted chunk
        """
        try:
            chunk_id = chunk.id or str(uuid.uuid4())
            
            # Convert embedding to list if it's a numpy array
            embedding = None
            if chunk.embedding is not None:
                if hasattr(chunk.embedding, 'tolist'):
                    embedding = chunk.embedding.tolist()
                else:
                    embedding = list(chunk.embedding)
            
            data = {
                'id': chunk_id,
                'content': chunk.content,
                'processed_content': chunk.processed_content,
                'embedding': embedding,
                'metadata': chunk.metadata.to_dict(),
                'cluster_id': chunk.cluster_id
            }
            
            result = self.client.table('content_chunks').upsert(data).execute()
            
            if result.data:
                logger.debug(f"Successfully inserted chunk {chunk_id}")
                return chunk_id
            else:
                raise Exception("No data returned from insert operation")
            
        except Exception as e:
            logger.error(f"Failed to insert chunk: {e}")
            raise
    
    def insert_chunks_batch(self, chunks: List[ContentChunk]) -> List[str]:
        """
        Insert multiple chunks efficiently.
        
        Args:
            chunks: List of ContentChunk objects
            
        Returns:
            List of inserted chunk IDs
        """
        if not chunks:
            return []
        
        try:
            chunk_ids = []
            batch_data = []
            
            for chunk in chunks:
                chunk_id = chunk.id or str(uuid.uuid4())
                chunk_ids.append(chunk_id)
                
                # Convert embedding to list if it's a numpy array
                embedding = None
                if chunk.embedding is not None:
                    if hasattr(chunk.embedding, 'tolist'):
                        embedding = chunk.embedding.tolist()
                    else:
                        embedding = list(chunk.embedding)
                
                data = {
                    'id': chunk_id,
                    'content': chunk.content,
                    'processed_content': chunk.processed_content,
                    'embedding': embedding,
                    'metadata': chunk.metadata.to_dict(),
                    'cluster_id': chunk.cluster_id
                }
                batch_data.append(data)
            
            # Use upsert for batch insert
            result = self.client.table('content_chunks').upsert(batch_data).execute()
            
            if result.data:
                logger.info(f"Successfully inserted {len(chunk_ids)} chunks")
                return chunk_ids
            else:
                raise Exception("No data returned from batch insert operation")
            
        except Exception as e:
            logger.error(f"Failed to insert chunks batch: {e}")
            raise
    
    def find_similar_chunks(self, embedding: List[float], threshold: float = 0.8, 
                           limit: int = 10, exclude_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Find similar chunks using vector similarity search.
        
        Args:
            embedding: Query embedding vector
            threshold: Minimum similarity threshold
            limit: Maximum number of results
            exclude_ids: Chunk IDs to exclude from results
            
        Returns:
            List of similar chunks with similarity scores
        """
        try:
            # Convert exclude_ids to UUID array format for PostgreSQL
            exclude_uuids = exclude_ids or []
            
            # Call the database function for vector similarity
            result = self.client.rpc(
                'match_chunks',
                {
                    'query_embedding': embedding,
                    'similarity_threshold': threshold,
                    'match_count': limit,
                    'exclude_ids': exclude_uuids
                }
            ).execute()
            
            if result.data:
                return result.data
            else:
                return []
            
        except Exception as e:
            logger.error(f"Failed to find similar chunks: {e}")
            return []
    def get_recent_chunks_from_db(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent chunks from database for duplicate checking.
        
        Args:
            hours: How many hours back to look
            limit: Maximum number of chunks to return
            
        Returns:
            List of recent chunk data
        """
        try:
            # Call the database function for recent chunks
            result = self.client.rpc(
                'get_recent_chunks',
                {
                    'hours_back': hours,
                    'limit_count': limit
                }
            ).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get recent chunks: {e}")
            return []
    
    
    def insert_cluster(self, cluster: ContentCluster) -> str:
        """
        Insert a content cluster into the database.
        
        Args:
            cluster: ContentCluster to insert
            
        Returns:
            ID of the inserted cluster
        """
        try:
            cluster_id = cluster.id or str(uuid.uuid4())
            
            # Convert centroid to list if it's a numpy array
            centroid = None
            if cluster.centroid is not None:
                if hasattr(cluster.centroid, 'tolist'):
                    centroid = cluster.centroid.tolist()
                else:
                    centroid = list(cluster.centroid)
            
            data = {
                'id': cluster_id,
                'centroid': centroid,
                'metadata': cluster.metadata.to_dict(),
                'chunk_count': cluster.chunk_count
            }
            
            result = self.client.table('content_clusters').upsert(data).execute()
            
            if result.data:
                logger.debug(f"Successfully inserted cluster {cluster_id}")
                return cluster_id
            else:
                raise Exception("No data returned from insert operation")
            
        except Exception as e:
            logger.error(f"Failed to insert cluster: {e}")
            raise
    
    def update_chunk_cluster_assignment(self, chunk_ids: List[str], cluster_id: str):
        """
        Update cluster assignment for multiple chunks.
        
        Args:
            chunk_ids: List of chunk IDs to update
            cluster_id: New cluster ID
        """
        if not chunk_ids:
            return
        
        try:
            # Update chunks one by one (Supabase doesn't support batch updates with WHERE IN through REST API)
            for chunk_id in chunk_ids:
                result = self.client.table('content_chunks').update({
                    'cluster_id': cluster_id,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', chunk_id).execute()
                
                if not result.data:
                    logger.warning(f"No result for updating chunk {chunk_id}")
            
            logger.info(f"Updated {len(chunk_ids)} chunks with cluster {cluster_id}")
            
        except Exception as e:
            logger.error(f"Failed to update chunk cluster assignments: {e}")
            raise
    
    def get_chunks_by_cluster(self, cluster_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks belonging to a cluster.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            List of chunk data
        """
        try:
            result = self.client.table('content_chunks').select(
                'id, content, processed_content, embedding, metadata, created_at'
            ).eq('cluster_id', cluster_id).order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get chunks by cluster: {e}")
            return []
    
    def insert_cluster_summary(self, summary: ClusterSummary) -> str:
        """
        Insert a cluster summary into the database.
        
        Args:
            summary: ClusterSummary to insert
            
        Returns:
            ID of the inserted summary
        """
        try:
            summary_id = summary.id or str(uuid.uuid4())
            
            metadata = {
                'generated_at': summary.generated_at.isoformat(),
                'model_used': summary.model_used,
                'confidence': summary.confidence
            }
            
            data = {
                'id': summary_id,
                'cluster_id': summary.cluster_id,
                'summary': summary.summary,
                'key_points': summary.key_points,
                'metadata': metadata,
                'model_used': summary.model_used,
                'confidence': summary.confidence,
                'word_count': summary.word_count
            }
            
            result = self.client.table('cluster_summaries').upsert(data).execute()
            
            if result.data:
                logger.debug(f"Successfully inserted cluster summary {summary_id}")
                return summary_id
            else:
                raise Exception("No data returned from insert operation")
            
        except Exception as e:
            logger.error(f"Failed to insert cluster summary: {e}")
            raise
    
    def get_recent_clusters(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent clusters with their summaries.
        
        Args:
            limit: Maximum number of clusters
            hours: How many hours back to look
            
        Returns:
            List of cluster data with summaries
        """
        try:
            # Calculate the timestamp for filtering
            from datetime import datetime, timedelta
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            
            # Get clusters with left join to summaries
            result = self.client.table('content_clusters').select(
                '''
                id, centroid, metadata, chunk_count, created_at, updated_at,
                cluster_summaries(summary, key_points, confidence, model_used)
                '''
            ).gte('created_at', cutoff_time).order('updated_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get recent clusters: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30):
        """
        Clean up old data from the database.
        
        Args:
            days: Number of days to keep
        """
        try:
            # Calculate cutoff timestamp
            from datetime import datetime, timedelta
            cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Delete old chunks
            chunks_result = self.client.table('content_chunks').delete().lt('created_at', cutoff_time).execute()
            
            # Delete old clusters
            clusters_result = self.client.table('content_clusters').delete().lt('created_at', cutoff_time).execute()
            
            logger.info(f"Cleaned up data older than {days} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def close(self):
        """Close connections (no-op for Supabase client)."""
        # Supabase client handles connection management internally
        logger.info("SupabaseManager closed (no action needed)")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.close()
