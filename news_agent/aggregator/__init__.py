"""
News Aggregator Module

This module provides semantic clustering and summarization of news content
retrieved by the PlannerAgent. It processes chunks of text from various sources,
clusters related content using semantic embeddings, and generates summaries
using AI models.

Main Components:
- AggregatorAgent: Main orchestrator class
- ContentChunk/ChunkMetadata: Data models for text chunks and metadata
- TextPreprocessor: Text cleaning and normalization
- EmbeddingManager: Sentence embeddings and vector storage
- ClusteringEngine: Semantic clustering using HDBSCAN
- DeduplicationEngine: Similarity-based duplicate removal
- ClusterScorer: Multi-factor scoring system
- GeminiSummarizer: AI-powered summary generation
- DatabaseManager: pgvector/Supabase integration

Integration Components:
- EnhancedPlannerAgent: PlannerAgent with aggregation
- RealtimeProcessor: Real-time processing capabilities
"""

from .models import ContentChunk, ChunkMetadata, ContentCluster, ClusterSummary, AggregatorOutput
from .config import AggregatorConfig, get_config
from .aggregator import AggregatorAgent, create_aggregator_agent
from .preprocessor import TextPreprocessor
from .embeddings import EmbeddingManager
from .clustering import ClusteringEngine
from .deduplication import DeduplicationEngine
from .scoring import ClusterScorer
from .summarizer import GeminiSummarizer
from .database import DatabaseManager

__all__ = [
    # Core models
    'ContentChunk',
    'ChunkMetadata',
    'ContentCluster',
    'ClusterSummary',
    'AggregatorOutput',
    
    # Configuration
    'AggregatorConfig',
    'get_config',
    
    # Main components
    'AggregatorAgent',
    'create_aggregator_agent',
    'TextPreprocessor',
    'EmbeddingManager',
    'ClusteringEngine',
    'DeduplicationEngine',
    'ClusterScorer',
    'GeminiSummarizer',
    'DatabaseManager'
]

__version__ = '1.0.0'
