"""
Sentence embedding generation and management for the News Aggregator.

This module provides semantic embedding capabilities using SentenceTransformers
with support for batch processing, caching, and pgvector storage integration.
"""

import logging
import asyncio
import numpy as np
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
import json
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor

try:
    from sentence_transformers import SentenceTransformer
    import torch
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .models import ContentChunk, EmbeddingVector
from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Simple file-based cache for embeddings to avoid recomputing.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize embedding cache."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "news_aggregator" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embedding_cache.pkl"
        self._cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, List[float]]:
        """Load cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load embedding cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
    
    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate cache key for text and model."""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, text: str, model_name: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        key = self._get_cache_key(text, model_name)
        return self._cache.get(key)
    
    def set(self, text: str, model_name: str, embedding: List[float]):
        """Store embedding in cache."""
        key = self._get_cache_key(text, model_name)
        self._cache[key] = embedding
        
        # Periodically save cache (every 100 entries)
        if len(self._cache) % 100 == 0:
            self._save_cache()
    
    def clear(self):
        """Clear cache."""
        self._cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def __del__(self):
        """Save cache on destruction."""
        self._save_cache()


class EmbeddingManager:
    """
    Manages sentence embedding generation and vector operations.
    
    Features:
    - SentenceTransformers integration
    - Batch processing for efficiency
    - Embedding caching
    - Similarity calculations
    - Async processing support
    """
    
    def __init__(self, config: EmbeddingConfig):
        """
        Initialize the embedding manager.
        
        Args:
            config: Embedding configuration parameters
        """
        self.config = config
        self.model = None
        self.device = None
        self.cache = EmbeddingCache(config.cache_dir) if config.cache_dir else None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required for embedding generation")
        
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available, some similarity functions disabled")
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the SentenceTransformer model."""
        try:
            logger.info(f"Loading embedding model: {self.config.model_name}")
            
            # Set device
            if self.config.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = self.config.device
            
            # Load model
            self.model = SentenceTransformer(
                self.config.model_name,
                device=self.device
            )
            
            # Set max sequence length
            if hasattr(self.model, 'max_seq_length'):
                self.model.max_seq_length = self.config.max_length
            
            logger.info(f"Embedding model loaded successfully on {self.device}")
            logger.info(f"Model dimension: {self.model.get_sentence_embedding_dimension()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension."""
        if self.model:
            return self.model.get_sentence_embedding_dimension()
        return 384  # Default for all-MiniLM-L6-v2
    
    def _preprocess_text_for_embedding(self, text: str) -> str:
        """
        Preprocess text before embedding generation.
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text ready for embedding
        """
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > self.config.max_length * 4:  # Rough character estimate
            text = text[:self.config.max_length * 4]
        
        # Basic cleaning for embedding
        text = text.strip()
        
        # Remove excessive newlines
        text = ' '.join(text.split())
        
        return text
    
    def encode_single(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            use_cache: Whether to use caching
            
        Returns:
            Embedding vector as list of floats
        """
        if not text:
            return [0.0] * self.embedding_dimension
        
        # Preprocess text
        processed_text = self._preprocess_text_for_embedding(text)
        
        # Check cache first
        if use_cache and self.cache:
            cached_embedding = self.cache.get(processed_text, self.config.model_name)
            if cached_embedding is not None:
                return cached_embedding
        
        try:
            # Generate embedding
            embedding = self.model.encode(
                processed_text,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False
            )
            
            # Convert to list
            embedding_list = embedding.tolist()
            
            # Cache result
            if use_cache and self.cache:
                self.cache.set(processed_text, self.config.model_name, embedding_list)
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * self.embedding_dimension
    
    def encode_batch(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            use_cache: Whether to use caching
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Preprocess texts
        processed_texts = [self._preprocess_text_for_embedding(text) for text in texts]
        
        # Check cache for all texts
        embeddings = []
        texts_to_embed = []
        indices_to_embed = []
        
        for i, text in enumerate(processed_texts):
            if use_cache and self.cache:
                cached_embedding = self.cache.get(text, self.config.model_name)
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                    continue
            
            # Need to embed this text
            embeddings.append(None)  # Placeholder
            texts_to_embed.append(text)
            indices_to_embed.append(i)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            try:
                logger.debug(f"Generating embeddings for {len(texts_to_embed)} texts")
                
                # Process in batches
                batch_size = self.config.batch_size
                new_embeddings = []
                
                for i in range(0, len(texts_to_embed), batch_size):
                    batch = texts_to_embed[i:i + batch_size]
                    
                    batch_embeddings = self.model.encode(
                        batch,
                        normalize_embeddings=self.config.normalize_embeddings,
                        show_progress_bar=len(texts_to_embed) > 50,
                        batch_size=len(batch)
                    )
                    
                    # Convert to list format
                    for embedding in batch_embeddings:
                        new_embeddings.append(embedding.tolist())
                
                # Fill in the embeddings
                for i, embedding in enumerate(new_embeddings):
                    idx = indices_to_embed[i]
                    embeddings[idx] = embedding
                    
                    # Cache the result
                    if use_cache and self.cache:
                        text = texts_to_embed[i]
                        self.cache.set(text, self.config.model_name, embedding)
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                # Fill with zero vectors
                zero_vector = [0.0] * self.embedding_dimension
                for idx in indices_to_embed:
                    embeddings[idx] = zero_vector
        
        return embeddings
    
    async def encode_batch_async(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """
        Asynchronously generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            use_cache: Whether to use caching
            
        Returns:
            List of embedding vectors
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            self.encode_batch, 
            texts, 
            use_cache
        )
    
    def embed_chunks(self, chunks: List[ContentChunk], use_cache: bool = True) -> List[ContentChunk]:
        """
        Generate embeddings for content chunks.
        
        Args:
            chunks: List of ContentChunk objects
            use_cache: Whether to use caching
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            return chunks
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        # Extract texts for embedding
        texts = []
        for chunk in chunks:
            # Use processed content if available, otherwise original content
            text = chunk.processed_content or chunk.content
            texts.append(text)
        
        # Generate embeddings
        embeddings = self.encode_batch(texts, use_cache)
        
        # Assign embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        logger.info("Embedding generation completed")
        return chunks
    
    async def embed_chunks_async(self, chunks: List[ContentChunk], use_cache: bool = True) -> List[ContentChunk]:
        """
        Asynchronously generate embeddings for content chunks.
        
        Args:
            chunks: List of ContentChunk objects
            use_cache: Whether to use caching
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            return chunks
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks (async)")
        
        # Extract texts for embedding
        texts = []
        for chunk in chunks:
            text = chunk.processed_content or chunk.content
            texts.append(text)
        
        # Generate embeddings asynchronously
        embeddings = await self.encode_batch_async(texts, use_cache)
        
        # Assign embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        logger.info("Async embedding generation completed")
        return chunks
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if not SKLEARN_AVAILABLE:
            # Fallback to manual cosine similarity
            return self._cosine_similarity_manual(embedding1, embedding2)
        
        try:
            # Reshape for sklearn
            emb1 = np.array(embedding1).reshape(1, -1)
            emb2 = np.array(embedding2).reshape(1, -1)
            
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def _cosine_similarity_manual(self, vec1: List[float], vec2: List[float]) -> float:
        """Manual cosine similarity calculation."""
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Manual similarity calculation failed: {e}")
            return 0.0
    
    def calculate_similarity_matrix(self, embeddings: List[List[float]]) -> np.ndarray:
        """
        Calculate pairwise similarity matrix for a list of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Similarity matrix as numpy array
        """
        if not embeddings:
            return np.array([])
        
        if not SKLEARN_AVAILABLE:
            # Manual calculation
            n = len(embeddings)
            similarity_matrix = np.zeros((n, n))
            
            for i in range(n):
                for j in range(i, n):
                    similarity = self._cosine_similarity_manual(embeddings[i], embeddings[j])
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
            
            return similarity_matrix
        
        try:
            # Use sklearn for efficient calculation
            embeddings_array = np.array(embeddings)
            return cosine_similarity(embeddings_array)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity matrix: {e}")
            n = len(embeddings)
            return np.eye(n)  # Return identity matrix as fallback
    
    def find_similar_chunks(self, target_chunk: ContentChunk, candidate_chunks: List[ContentChunk], 
                          threshold: float = 0.8, top_k: Optional[int] = None) -> List[Tuple[ContentChunk, float]]:
        """
        Find chunks similar to a target chunk.
        
        Args:
            target_chunk: Chunk to find similarities for
            candidate_chunks: List of chunks to search in
            threshold: Minimum similarity threshold
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, similarity_score) tuples, sorted by similarity
        """
        if not target_chunk.embedding or not candidate_chunks:
            return []
        
        similar_chunks = []
        
        for chunk in candidate_chunks:
            if not chunk.embedding or chunk.id == target_chunk.id:
                continue
            
            similarity = self.calculate_similarity(target_chunk.embedding, chunk.embedding)
            
            if similarity >= threshold:
                similar_chunks.append((chunk, similarity))
        
        # Sort by similarity (descending)
        similar_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results if requested
        if top_k:
            similar_chunks = similar_chunks[:top_k]
        
        return similar_chunks
    
    def compute_centroid(self, embeddings: List[List[float]]) -> List[float]:
        """
        Compute the centroid of a list of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Centroid embedding vector
        """
        if not embeddings:
            return [0.0] * self.embedding_dimension
        
        try:
            embeddings_array = np.array(embeddings)
            centroid = np.mean(embeddings_array, axis=0)
            return centroid.tolist()
            
        except Exception as e:
            logger.error(f"Failed to compute centroid: {e}")
            return [0.0] * self.embedding_dimension
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
