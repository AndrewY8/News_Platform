"""
Data models for the News Aggregator system.

This module defines the core data structures used throughout the aggregation pipeline,
including content chunks, metadata, clusters, and summaries.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


class SourceType(Enum):
    """Enumeration of different source types for content classification."""
    BREAKING_NEWS = "breaking_news"
    FINANCIAL_NEWS = "financial_news"
    SEC_FILING = "sec_filing"
    GENERAL_NEWS = "general_news"
    SOCIAL_MEDIA = "social_media"
    BLOG_POST = "blog_post"
    PRESS_RELEASE = "press_release"


class ReliabilityTier(Enum):
    """Source reliability classification."""
    TIER_1 = "tier_1"  # Official sources (SEC, company announcements)
    TIER_2 = "tier_2"  # Major news outlets (Reuters, Bloomberg, AP)
    TIER_3 = "tier_3"  # Established media (CNN, CNBC, WSJ)
    TIER_4 = "tier_4"  # Smaller outlets and trade publications
    TIER_5 = "tier_5"  # Blogs, social media, unverified sources


# Source reliability scoring mapping
RELIABILITY_SCORES = {
    ReliabilityTier.TIER_1: 1.0,
    ReliabilityTier.TIER_2: 0.9,
    ReliabilityTier.TIER_3: 0.8,
    ReliabilityTier.TIER_4: 0.6,
    ReliabilityTier.TIER_5: 0.4
}


@dataclass
class ChunkMetadata:
    """
    Metadata associated with a content chunk.
    
    Attributes:
        timestamp: When the content was published/retrieved
        source: Source domain or publication name
        ticker: Associated stock ticker symbol (if applicable)
        topic: Main topic/category of the content
        url: Original source URL
        title: Article/content title
        author: Author name (if available)
        source_type: Classification of source type
        reliability_tier: Reliability classification of the source
        source_retriever: Which retriever found this content
        language: Content language (ISO 639-1 code)
        word_count: Number of words in the content
        image_urls: Associated image URLs
    """
    timestamp: datetime
    source: str
    url: str
    title: str
    topic: str
    source_type: SourceType
    reliability_tier: ReliabilityTier
    source_retriever: str
    ticker: Optional[str] = None
    author: Optional[str] = None
    language: str = "en"
    word_count: int = 0
    image_urls: List[str] = field(default_factory=list)
    
    @property
    def source_reliability_score(self) -> float:
        """Get numerical reliability score for this source."""
        return RELIABILITY_SCORES[self.reliability_tier]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "ticker": self.ticker,
            "topic": self.topic,
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "source_type": self.source_type.value,
            "reliability_tier": self.reliability_tier.value,
            "source_reliability_score": self.source_reliability_score,
            "source_retriever": self.source_retriever,
            "language": self.language,
            "word_count": self.word_count,
            "image_urls": self.image_urls
        }


@dataclass
class ContentChunk:
    """
    A chunk of text content with associated metadata and embedding.
    
    Attributes:
        id: Unique identifier for the chunk
        content: The actual text content
        metadata: Associated metadata
        embedding: Semantic embedding vector (384-dimensional for SentenceTransformers)
        processed_content: Cleaned and normalized version of content
        cluster_id: ID of the cluster this chunk belongs to (if assigned)
    """
    id: str
    content: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None
    processed_content: Optional[str] = None
    cluster_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate UUID if no ID provided."""
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def embedding_dimension(self) -> Optional[int]:
        """Get the dimension of the embedding vector."""
        return len(self.embedding) if self.embedding else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "processed_content": self.processed_content,
            "metadata": self.metadata.to_dict(),
            "embedding": self.embedding,
            "cluster_id": self.cluster_id
        }


@dataclass
class SourceReference:
    """
    Reference to a source document within a cluster.
    
    Attributes:
        url: Source URL
        title: Article title
        author: Author name (if available)
        timestamp: Publication timestamp
        excerpt: Key excerpt from the article
        relevance_score: How relevant this source is to the cluster
    """
    url: str
    title: str
    timestamp: datetime
    excerpt: str
    author: Optional[str] = None
    relevance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert source reference to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "excerpt": self.excerpt,
            "relevance_score": self.relevance_score
        }


@dataclass
class ClusterMetadata:
    """
    Metadata for a content cluster.
    
    Attributes:
        primary_ticker: Main ticker symbol associated with cluster
        topics: List of topics covered in the cluster
        time_range: Tuple of (earliest, latest) timestamps
        source_types: Types of sources in the cluster
        confidence_score: Confidence in cluster coherence (0-1)
        cluster_size: Number of chunks in the cluster
        dominant_language: Primary language of cluster content
    """
    confidence_score: float
    cluster_size: int
    primary_ticker: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    time_range: Optional[tuple] = None
    source_types: List[SourceType] = field(default_factory=list)
    dominant_language: str = "en"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cluster metadata to dictionary."""
        return {
            "primary_ticker": self.primary_ticker,
            "topics": self.topics,
            "time_range": [t.isoformat() for t in self.time_range] if self.time_range else None,
            "source_types": [st.value for st in self.source_types],
            "confidence_score": self.confidence_score,
            "cluster_size": self.cluster_size,
            "dominant_language": self.dominant_language
        }


@dataclass
class ContentCluster:
    """
    A cluster of related content chunks.
    
    Attributes:
        id: Unique cluster identifier
        chunks: List of content chunks in this cluster
        centroid: Cluster centroid embedding
        metadata: Cluster metadata
        created_at: When cluster was created
        updated_at: When cluster was last updated
        summary: Generated summary (if available)
    """
    id: str
    chunks: List[ContentChunk]
    metadata: ClusterMetadata
    centroid: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    summary: Optional['ClusterSummary'] = None
    
    def __post_init__(self):
        """Generate UUID if no ID provided."""
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def chunk_count(self) -> int:
        """Number of chunks in this cluster."""
        return len(self.chunks)
    
    @property
    def source_count(self) -> int:
        """Number of unique sources in this cluster."""
        return len(set(chunk.metadata.url for chunk in self.chunks))
    
    def get_sources(self) -> List[SourceReference]:
        """Extract source references from cluster chunks."""
        sources = []
        for chunk in self.chunks:
            excerpt = chunk.processed_content or chunk.content
            # Truncate excerpt to reasonable length
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + "..."
            
            source = SourceReference(
                url=chunk.metadata.url,
                title=chunk.metadata.title,
                author=chunk.metadata.author,
                timestamp=chunk.metadata.timestamp,
                excerpt=excerpt,
                relevance_score=1.0  # TODO: Calculate based on similarity to centroid
            )
            sources.append(source)
        
        return sources
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cluster to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "chunk_count": self.chunk_count,
            "source_count": self.source_count,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sources": [source.to_dict() for source in self.get_sources()],
            "summary": self.summary.to_dict() if self.summary else None
        }


@dataclass
class ClusterSummary:
    """
    AI-generated summary of a content cluster.
    
    Attributes:
        id: Unique summary identifier
        cluster_id: Associated cluster ID
        summary: The generated summary text
        key_points: List of key points extracted
        generated_at: When summary was generated
        model_used: AI model used for generation
        confidence: Confidence in summary quality (0-1)
        word_count: Number of words in summary
    """
    id: str
    cluster_id: str
    summary: str
    key_points: List[str]
    generated_at: datetime
    model_used: str
    confidence: float = 1.0
    word_count: int = 0
    
    def __post_init__(self):
        """Generate UUID if no ID provided and calculate word count."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.word_count == 0 and self.summary:
            self.word_count = len(self.summary.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "generated_at": self.generated_at.isoformat(),
            "model_used": self.model_used,
            "confidence": self.confidence,
            "word_count": self.word_count
        }


@dataclass
class AggregatorOutput:
    """
    Final output from the aggregator system.
    
    Attributes:
        clusters: List of content clusters with summaries
        processing_stats: Statistics about the aggregation process
        generated_at: When output was generated
        query_context: Original query or context that triggered aggregation
    """
    clusters: List[ContentCluster]
    processing_stats: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    query_context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary for JSON serialization."""
        return {
            "clusters": [cluster.to_dict() for cluster in self.clusters],
            "processing_stats": self.processing_stats,
            "generated_at": self.generated_at.isoformat(),
            "query_context": self.query_context
        }
    
    @property
    def total_clusters(self) -> int:
        """Total number of clusters."""
        return len(self.clusters)
    
    @property
    def total_sources(self) -> int:
        """Total number of unique sources across all clusters."""
        all_sources = set()
        for cluster in self.clusters:
            for chunk in cluster.chunks:
                all_sources.add(chunk.metadata.url)
        return len(all_sources)


# Type aliases for convenience
EmbeddingVector = List[float]
ChunkList = List[ContentChunk]
ClusterList = List[ContentCluster]
