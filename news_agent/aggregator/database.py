"""
Database utilities for pgvector integration with Supabase.

This module provides database connection management, schema creation,
and CRUD operations for storing content chunks, embeddings, and clusters
in a PostgreSQL database with pgvector extension.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime
import json
import uuid

try:
    import asyncpg
    import psycopg2
    from psycopg2.extras import Json, DictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import sqlalchemy as sa
    from sqlalchemy import create_engine, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

import numpy as np
from .models import ContentChunk, ContentCluster, ClusterSummary
from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and operations for the aggregator system.
    
    Features:
    - PostgreSQL with pgvector extension support
    - Async and sync connection management
    - Schema creation and management
    - CRUD operations for chunks, clusters, and summaries
    - Vector similarity search
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize database manager.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.engine = None
        self.async_engine = None
        self.connection_pool = None
        
        if not config.connection_string:
            raise ValueError("Database connection string is required")
        
        if not PSYCOPG2_AVAILABLE and not SQLALCHEMY_AVAILABLE:
            raise ImportError("Either psycopg2 or SQLAlchemy is required for database operations")
        
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize database connections."""
        try:
            if SQLALCHEMY_AVAILABLE:
                # SQLAlchemy engines
                self.engine = create_engine(
                    self.config.connection_string,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    echo=False
                )
                
                # Async engine for async operations
                async_connection_string = self.config.connection_string.replace('postgresql://', 'postgresql+asyncpg://')
                self.async_engine = create_async_engine(
                    async_connection_string,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    echo=False
                )
                
                logger.info("SQLAlchemy database connections initialized")
            
            elif PSYCOPG2_AVAILABLE:
                # Direct psycopg2 connection pool
                from psycopg2 import pool
                self.connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=self.config.pool_size,
                    dsn=self.config.connection_string
                )
                logger.info("psycopg2 connection pool initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    def create_schema(self):
        """
        Create database schema with pgvector extension and tables.
        """
        schema_sql = f"""
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Create content_chunks table
        CREATE TABLE IF NOT EXISTS content_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT NOT NULL,
            processed_content TEXT,
            embedding vector({self.config.vector_dimension}),
            metadata JSONB NOT NULL,
            cluster_id UUID,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Create content_clusters table
        CREATE TABLE IF NOT EXISTS content_clusters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            centroid vector({self.config.vector_dimension}),
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
        USING {self.config.index_type} (embedding vector_cosine_ops) 
        WITH (lists = {self.config.index_lists});
        
        CREATE INDEX IF NOT EXISTS idx_clusters_centroid ON content_clusters 
        USING {self.config.index_type} (centroid vector_cosine_ops)
        WITH (lists = {self.config.index_lists});
        
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
        """
        
        try:
            if self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text(schema_sql))
                    conn.commit()
                    logger.info("Database schema created successfully")
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(schema_sql)
                    conn.commit()
                    logger.info("Database schema created successfully")
                finally:
                    self.connection_pool.putconn(conn)
                    
        except Exception as e:
            logger.error(f"Failed to create database schema: {e}")
            raise
    
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
            
            insert_sql = """
            INSERT INTO content_chunks (id, content, processed_content, embedding, metadata, cluster_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                processed_content = EXCLUDED.processed_content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                cluster_id = EXCLUDED.cluster_id,
                updated_at = NOW()
            RETURNING id;
            """
            
            if self.engine:
                with self.engine.connect() as conn:
                    result = conn.execute(text(insert_sql), {
                        'id': chunk_id,
                        'content': chunk.content,
                        'processed_content': chunk.processed_content,
                        'embedding': str(chunk.embedding) if chunk.embedding else None,
                        'metadata': json.dumps(chunk.metadata.to_dict()),
                        'cluster_id': chunk.cluster_id
                    })
                    conn.commit()
                    return chunk_id
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(insert_sql, (
                            chunk_id,
                            chunk.content,
                            chunk.processed_content,
                            str(chunk.embedding) if chunk.embedding else None,
                            Json(chunk.metadata.to_dict()),
                            chunk.cluster_id
                        ))
                    conn.commit()
                    return chunk_id
                finally:
                    self.connection_pool.putconn(conn)
            
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
            
            if self.engine:
                with self.engine.connect() as conn:
                    for chunk in chunks:
                        chunk_id = chunk.id or str(uuid.uuid4())
                        chunk_ids.append(chunk_id)
                        
                        conn.execute(text("""
                            INSERT INTO content_chunks (id, content, processed_content, embedding, metadata, cluster_id)
                            VALUES (:id, :content, :processed_content, :embedding, :metadata, :cluster_id)
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content,
                                processed_content = EXCLUDED.processed_content,
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata,
                                cluster_id = EXCLUDED.cluster_id,
                                updated_at = NOW()
                        """), {
                            'id': chunk_id,
                            'content': chunk.content,
                            'processed_content': chunk.processed_content,
                            'embedding': str(chunk.embedding) if chunk.embedding else None,
                            'metadata': json.dumps(chunk.metadata.to_dict()),
                            'cluster_id': chunk.cluster_id
                        })
                    
                    conn.commit()
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        for chunk in chunks:
                            chunk_id = chunk.id or str(uuid.uuid4())
                            chunk_ids.append(chunk_id)
                            
                            cur.execute("""
                                INSERT INTO content_chunks (id, content, processed_content, embedding, metadata, cluster_id)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id) DO UPDATE SET
                                    content = EXCLUDED.content,
                                    processed_content = EXCLUDED.processed_content,
                                    embedding = EXCLUDED.embedding,
                                    metadata = EXCLUDED.metadata,
                                    cluster_id = EXCLUDED.cluster_id,
                                    updated_at = NOW()
                            """, (
                                chunk_id,
                                chunk.content,
                                chunk.processed_content,
                                str(chunk.embedding) if chunk.embedding else None,
                                Json(chunk.metadata.to_dict()),
                                chunk.cluster_id
                            ))
                    conn.commit()
                finally:
                    self.connection_pool.putconn(conn)
            
            logger.info(f"Successfully inserted {len(chunk_ids)} chunks")
            return chunk_ids
            
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
            exclude_clause = ""
            if exclude_ids:
                exclude_clause = f"AND id NOT IN ({','.join(['%s'] * len(exclude_ids))})"
            
            query_sql = f"""
            SELECT id, content, processed_content, metadata, cluster_id,
                   1 - (embedding <=> %s) as similarity
            FROM content_chunks
            WHERE embedding IS NOT NULL
            {exclude_clause}
            AND 1 - (embedding <=> %s) >= %s
            ORDER BY embedding <=> %s
            LIMIT %s;
            """
            
            embedding_str = str(embedding)
            params = [embedding_str, embedding_str, threshold, embedding_str, limit]
            if exclude_ids:
                params = [embedding_str] + exclude_ids + [embedding_str, threshold, embedding_str, limit]
            
            if self.engine:
                with self.engine.connect() as conn:
                    result = conn.execute(text(query_sql), params)
                    return [dict(row) for row in result]
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute(query_sql, params)
                        return [dict(row) for row in cur.fetchall()]
                finally:
                    self.connection_pool.putconn(conn)
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to find similar chunks: {e}")
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
            
            insert_sql = """
            INSERT INTO content_clusters (id, centroid, metadata, chunk_count)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                centroid = EXCLUDED.centroid,
                metadata = EXCLUDED.metadata,
                chunk_count = EXCLUDED.chunk_count,
                updated_at = NOW()
            RETURNING id;
            """
            
            if self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text(insert_sql), {
                        'id': cluster_id,
                        'centroid': str(cluster.centroid) if cluster.centroid else None,
                        'metadata': json.dumps(cluster.metadata.to_dict()),
                        'chunk_count': cluster.chunk_count
                    })
                    conn.commit()
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(insert_sql, (
                            cluster_id,
                            str(cluster.centroid) if cluster.centroid else None,
                            Json(cluster.metadata.to_dict()),
                            cluster.chunk_count
                        ))
                    conn.commit()
                finally:
                    self.connection_pool.putconn(conn)
            
            return cluster_id
            
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
            placeholders = ','.join(['%s'] * len(chunk_ids))
            update_sql = f"""
            UPDATE content_chunks 
            SET cluster_id = %s, updated_at = NOW()
            WHERE id IN ({placeholders});
            """
            
            if self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text(update_sql), [cluster_id] + chunk_ids)
                    conn.commit()
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(update_sql, [cluster_id] + chunk_ids)
                    conn.commit()
                finally:
                    self.connection_pool.putconn(conn)
            
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
            query_sql = """
            SELECT id, content, processed_content, embedding, metadata, created_at
            FROM content_chunks
            WHERE cluster_id = %s
            ORDER BY created_at DESC;
            """
            
            if self.engine:
                with self.engine.connect() as conn:
                    result = conn.execute(text(query_sql), [cluster_id])
                    return [dict(row) for row in result]
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute(query_sql, (cluster_id,))
                        return [dict(row) for row in cur.fetchall()]
                finally:
                    self.connection_pool.putconn(conn)
            
            return []
            
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
            
            insert_sql = """
            INSERT INTO cluster_summaries (id, cluster_id, summary, key_points, metadata, model_used, confidence, word_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                summary = EXCLUDED.summary,
                key_points = EXCLUDED.key_points,
                metadata = EXCLUDED.metadata,
                model_used = EXCLUDED.model_used,
                confidence = EXCLUDED.confidence,
                word_count = EXCLUDED.word_count
            RETURNING id;
            """
            
            metadata = {
                'generated_at': summary.generated_at.isoformat(),
                'model_used': summary.model_used,
                'confidence': summary.confidence
            }
            
            if self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text(insert_sql), {
                        'id': summary_id,
                        'cluster_id': summary.cluster_id,
                        'summary': summary.summary,
                        'key_points': json.dumps(summary.key_points),
                        'metadata': json.dumps(metadata),
                        'model_used': summary.model_used,
                        'confidence': summary.confidence,
                        'word_count': summary.word_count
                    })
                    conn.commit()
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(insert_sql, (
                            summary_id,
                            summary.cluster_id,
                            summary.summary,
                            Json(summary.key_points),
                            Json(metadata),
                            summary.model_used,
                            summary.confidence,
                            summary.word_count
                        ))
                    conn.commit()
                finally:
                    self.connection_pool.putconn(conn)
            
            return summary_id
            
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
            query_sql = """
            SELECT c.id, c.centroid, c.metadata, c.chunk_count, c.created_at, c.updated_at,
                   s.summary, s.key_points, s.confidence, s.model_used
            FROM content_clusters c
            LEFT JOIN cluster_summaries s ON c.id = s.cluster_id
            WHERE c.created_at > NOW() - INTERVAL '%s hours'
            ORDER BY c.updated_at DESC
            LIMIT %s;
            """
            
            if self.engine:
                with self.engine.connect() as conn:
                    result = conn.execute(text(query_sql), [hours, limit])
                    return [dict(row) for row in result]
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor(cursor_factory=DictCursor) as cur:
                        cur.execute(query_sql, (hours, limit))
                        return [dict(row) for row in cur.fetchall()]
                finally:
                    self.connection_pool.putconn(conn)
            
            return []
            
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
            cleanup_sql = """
            DELETE FROM content_chunks WHERE created_at < NOW() - INTERVAL '%s days';
            DELETE FROM content_clusters WHERE created_at < NOW() - INTERVAL '%s days';
            """
            
            if self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text(cleanup_sql), [days, days])
                    conn.commit()
                    
            elif self.connection_pool:
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        cur.execute(cleanup_sql, (days, days))
                    conn.commit()
                finally:
                    self.connection_pool.putconn(conn)
            
            logger.info(f"Cleaned up data older than {days} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def close(self):
        """Close database connections."""
        try:
            if self.engine:
                self.engine.dispose()
            if self.async_engine:
                asyncio.create_task(self.async_engine.dispose())
            if self.connection_pool:
                self.connection_pool.closeall()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.close()
