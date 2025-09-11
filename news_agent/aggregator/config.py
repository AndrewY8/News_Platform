"""
Configuration system for the News Aggregator.

This module defines configuration parameters for all aggregator components,
allowing easy tuning of clustering, scoring, and processing parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import os
from pathlib import Path


@dataclass
class EmbeddingConfig:
    """Configuration for text embedding generation."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    max_length: int = 512
    normalize_embeddings: bool = True
    device: str = "auto"  # "auto", "cpu", or "cuda"
    cache_dir: Optional[str] = None


@dataclass
class ClusteringConfig:
    """Configuration for HDBSCAN clustering."""
    min_cluster_size: int = 3
    min_samples: int = 2
    metric: str = "euclidean"
    cluster_selection_method: str = "eom"  # "eom" or "leaf"
    cluster_selection_epsilon: float = 0.0
    alpha: float = 1.0
    max_cluster_size: int = 50  # Prevent overly large clusters
    similarity_threshold: float = 0.8  # For cluster merging decisions


@dataclass
class DeduplicationConfig:
    """Configuration for content deduplication."""
    similarity_threshold: float = 0.85
    title_similarity_weight: float = 0.4
    content_similarity_weight: float = 0.6
    use_fuzzy_matching: bool = True
    fuzzy_ratio_threshold: int = 85
    min_content_length: int = 50  # Minimum content length to consider


@dataclass
class ScoringConfig:
    """Configuration for cluster scoring system."""
    recency_weight: float = 0.4
    reliability_weight: float = 0.35
    relevance_weight: float = 0.25
    time_decay_hours: int = 24  # Hours for time decay function
    max_time_decay: float = 0.1  # Minimum score multiplier for old content
    breaking_news_boost: float = 1.5  # Multiplier for breaking news
    source_diversity_bonus: float = 0.1  # Bonus for clusters with diverse sources


@dataclass
class PreprocessingConfig:
    """Configuration for text preprocessing."""
    remove_html: bool = True
    remove_urls: bool = True
    remove_email: bool = True
    remove_phone: bool = True
    normalize_whitespace: bool = True
    remove_boilerplate: bool = True
    min_sentence_length: int = 10
    max_chunk_size: int = 1000
    chunk_overlap: int = 100
    language_detection: bool = True
    supported_languages: List[str] = field(default_factory=lambda: ["en", "es", "fr", "de"])


@dataclass
class SummarizerConfig:
    """Configuration for AI summarization."""
    model_provider: str = "gemini"  # "gemini", "openai", "anthropic"
    model_name: str = "gemini-1.5-flash"
    max_input_tokens: int = 30000
    max_output_tokens: int = 500
    temperature: float = 0.3
    batch_size: int = 5
    retry_attempts: int = 3
    retry_delay: float = 1.0  # Initial retry delay in seconds
    timeout: int = 30  # Request timeout in seconds


@dataclass
class DatabaseConfig:
    """Configuration for database connections."""
    connection_string: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    vector_dimension: int = 384  # For all-MiniLM-L6-v2
    index_type: str = "ivfflat"  # "ivfflat" or "hnsw"
    index_lists: int = 100  # For IVFFlat index


@dataclass
class ProcessingConfig:
    """Configuration for processing pipeline."""
    batch_interval_seconds: int = 30
    max_batch_size: int = 50
    max_clusters_output: int = 10
    enable_real_time: bool = True
    max_concurrent_tasks: int = 10
    chunk_timeout_seconds: int = 300
    enable_metrics: bool = True
    log_level: str = "INFO"


@dataclass
class AggregatorConfig:
    """Main configuration class containing all component configurations."""
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    deduplication: DeduplicationConfig = field(default_factory=DeduplicationConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    summarizer: SummarizerConfig = field(default_factory=SummarizerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    @classmethod
    def from_env(cls) -> 'AggregatorConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Database configuration from environment
        if db_url := os.getenv("DATABASE_URL"):
            config.database.connection_string = db_url
        
        # Gemini API configuration
        if api_key := os.getenv("GEMINI_API_KEY"):
            # Store API key in summarizer config (to be used by summarizer)
            config.summarizer.api_key = api_key
        
        # Embedding model configuration
        if model_name := os.getenv("EMBEDDING_MODEL"):
            config.embedding.model_name = model_name
        
        # Processing configuration
        if batch_size := os.getenv("BATCH_SIZE"):
            config.processing.max_batch_size = int(batch_size)
        
        if interval := os.getenv("BATCH_INTERVAL"):
            config.processing.batch_interval_seconds = int(interval)
        
        # Clustering configuration
        if min_cluster_size := os.getenv("MIN_CLUSTER_SIZE"):
            config.clustering.min_cluster_size = int(min_cluster_size)
        
        if similarity_threshold := os.getenv("SIMILARITY_THRESHOLD"):
            config.clustering.similarity_threshold = float(similarity_threshold)
        
        # Scoring weights
        if recency_weight := os.getenv("RECENCY_WEIGHT"):
            config.scoring.recency_weight = float(recency_weight)
        
        if reliability_weight := os.getenv("RELIABILITY_WEIGHT"):
            config.scoring.reliability_weight = float(reliability_weight)
        
        if relevance_weight := os.getenv("RELEVANCE_WEIGHT"):
            config.scoring.relevance_weight = float(relevance_weight)
        
        return config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'AggregatorConfig':
        """Load configuration from a JSON or YAML file."""
        import json
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            if config_path.endswith('.json'):
                config_data = json.load(f)
            elif config_path.endswith(('.yml', '.yaml')):
                try:
                    import yaml
                    config_data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required to load YAML configuration files")
            else:
                raise ValueError("Configuration file must be JSON (.json) or YAML (.yml/.yaml)")
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AggregatorConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        for section_name, section_config in config_dict.items():
            if hasattr(config, section_name) and isinstance(section_config, dict):
                section_obj = getattr(config, section_name)
                for key, value in section_config.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "embedding": {
                "model_name": self.embedding.model_name,
                "batch_size": self.embedding.batch_size,
                "max_length": self.embedding.max_length,
                "normalize_embeddings": self.embedding.normalize_embeddings,
                "device": self.embedding.device,
                "cache_dir": self.embedding.cache_dir
            },
            "clustering": {
                "min_cluster_size": self.clustering.min_cluster_size,
                "min_samples": self.clustering.min_samples,
                "metric": self.clustering.metric,
                "cluster_selection_method": self.clustering.cluster_selection_method,
                "similarity_threshold": self.clustering.similarity_threshold,
                "max_cluster_size": self.clustering.max_cluster_size
            },
            "deduplication": {
                "similarity_threshold": self.deduplication.similarity_threshold,
                "title_similarity_weight": self.deduplication.title_similarity_weight,
                "content_similarity_weight": self.deduplication.content_similarity_weight,
                "use_fuzzy_matching": self.deduplication.use_fuzzy_matching,
                "min_content_length": self.deduplication.min_content_length
            },
            "scoring": {
                "recency_weight": self.scoring.recency_weight,
                "reliability_weight": self.scoring.reliability_weight,
                "relevance_weight": self.scoring.relevance_weight,
                "time_decay_hours": self.scoring.time_decay_hours,
                "breaking_news_boost": self.scoring.breaking_news_boost
            },
            "preprocessing": {
                "remove_html": self.preprocessing.remove_html,
                "remove_urls": self.preprocessing.remove_urls,
                "normalize_whitespace": self.preprocessing.normalize_whitespace,
                "min_sentence_length": self.preprocessing.min_sentence_length,
                "max_chunk_size": self.preprocessing.max_chunk_size,
                "supported_languages": self.preprocessing.supported_languages
            },
            "summarizer": {
                "model_provider": self.summarizer.model_provider,
                "model_name": self.summarizer.model_name,
                "max_input_tokens": self.summarizer.max_input_tokens,
                "max_output_tokens": self.summarizer.max_output_tokens,
                "temperature": self.summarizer.temperature,
                "batch_size": self.summarizer.batch_size
            },
            "processing": {
                "batch_interval_seconds": self.processing.batch_interval_seconds,
                "max_batch_size": self.processing.max_batch_size,
                "max_clusters_output": self.processing.max_clusters_output,
                "enable_real_time": self.processing.enable_real_time,
                "log_level": self.processing.log_level
            }
        }
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        # Validate weights sum to 1
        total_weight = (
            self.scoring.recency_weight + 
            self.scoring.reliability_weight + 
            self.scoring.relevance_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")
        
        # Validate clustering parameters
        if self.clustering.min_cluster_size < 2:
            raise ValueError("min_cluster_size must be at least 2")
        
        if self.clustering.min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        
        # Validate similarity thresholds
        if not 0 <= self.clustering.similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        
        if not 0 <= self.deduplication.similarity_threshold <= 1:
            raise ValueError("deduplication similarity_threshold must be between 0 and 1")
        
        # Validate processing parameters
        if self.processing.max_batch_size < 1:
            raise ValueError("max_batch_size must be at least 1")
        
        if self.processing.batch_interval_seconds < 1:
            raise ValueError("batch_interval_seconds must be at least 1")
        
        return True


# Default configuration instance
DEFAULT_CONFIG = AggregatorConfig()


def get_config() -> AggregatorConfig:
    """
    Get configuration instance.
    
    Priority order:
    1. Environment variables
    2. Configuration file (if AGGREGATOR_CONFIG_FILE is set)
    3. Default configuration
    """
    config_file = os.getenv("AGGREGATOR_CONFIG_FILE")
    
    if config_file:
        try:
            config = AggregatorConfig.from_file(config_file)
        except (FileNotFoundError, ValueError) as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
            config = AggregatorConfig.from_env()
    else:
        config = AggregatorConfig.from_env()
    
    # Validate configuration
    config.validate()
    
    return config
