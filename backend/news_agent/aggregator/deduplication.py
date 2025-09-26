"""
Content deduplication engine using cosine similarity and fuzzy matching.

This module provides comprehensive deduplication capabilities for news content,
using both semantic similarity (embeddings) and traditional text matching techniques
to identify and remove duplicate articles.
"""

import logging
import hashlib
from typing import List, Set, Dict, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime
import re

try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

try:
    from difflib import SequenceMatcher
    DIFFLIB_AVAILABLE = True
except ImportError:
    DIFFLIB_AVAILABLE = False

import numpy as np
from .models import ContentChunk, ChunkMetadata
from .config import DeduplicationConfig
from .embeddings import EmbeddingManager

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Multi-layered deduplication engine for news content.
    
    Features:
    - Exact URL deduplication
    - Title-based fuzzy matching
    - Content semantic similarity using embeddings
    - Combined similarity scoring
    - Duplicate group management
    - Quality-based duplicate resolution
    """
    
    def __init__(self, config: DeduplicationConfig, embedding_manager: Optional[EmbeddingManager] = None):
        """
        Initialize the deduplication engine.
        
        Args:
            config: Deduplication configuration
            embedding_manager: Optional embedding manager for semantic similarity
        """
        self.config = config
        self.embedding_manager = embedding_manager
        
        # Caches for efficiency
        self.url_cache = set()
        self.title_hashes = set()
        self.content_hashes = set()
        
        if config.use_fuzzy_matching and not FUZZYWUZZY_AVAILABLE:
            logger.warning("fuzzywuzzy not available, falling back to difflib")
        
        if not DIFFLIB_AVAILABLE:
            logger.warning("difflib not available, some text matching features disabled")
    
    def deduplicate_chunks(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """
        Remove duplicates from a list of content chunks.
        
        Args:
            chunks: List of ContentChunk objects
            
        Returns:
            Deduplicated list of ContentChunk objects
        """
        if not chunks:
            return []
        
        logger.info(f"Starting deduplication of {len(chunks)} chunks")
        
        # Stage 1: Filter out chunks with insufficient content
        valid_chunks = self._filter_valid_chunks(chunks)
        logger.info(f"After content length filtering: {len(valid_chunks)} chunks")
        
        # Stage 2: Exact URL deduplication
        url_deduped = self._deduplicate_by_url(valid_chunks)
        logger.info(f"After URL deduplication: {len(url_deduped)} chunks")
        
        # Stage 3: Title-based deduplication
        title_deduped = self._deduplicate_by_title(url_deduped)
        logger.info(f"After title deduplication: {len(title_deduped)} chunks")
        
        # Stage 4: Content hash deduplication
        hash_deduped = self._deduplicate_by_content_hash(title_deduped)
        logger.info(f"After content hash deduplication: {len(hash_deduped)} chunks")
        
        # Stage 5: Semantic similarity deduplication
        if self.embedding_manager:
            semantic_deduped = self._deduplicate_by_semantic_similarity(hash_deduped)
            logger.info(f"After semantic deduplication: {len(semantic_deduped)} chunks")
        else:
            semantic_deduped = hash_deduped
            logger.info("Skipping semantic deduplication (no embedding manager)")
        
        # Stage 6: Final fuzzy content matching
        final_deduped = self._deduplicate_by_fuzzy_content(semantic_deduped)
        logger.info(f"Final deduplication result: {len(final_deduped)} chunks")
        
        # Clear caches for next run
        self._clear_caches()
        
        return final_deduped
    
    def _filter_valid_chunks(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Filter chunks with valid content length."""
        valid_chunks = []
        
        for chunk in chunks:
            content = chunk.processed_content or chunk.content
            if len(content) >= self.config.min_content_length:
                valid_chunks.append(chunk)
        
        return valid_chunks
    
    def _deduplicate_by_url(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Remove duplicates based on exact URL matching."""
        seen_urls = set()
        deduped = []
        
        for chunk in chunks:
            url = chunk.metadata.url
            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append(chunk)
            else:
                logger.debug(f"Duplicate URL found: {url}")
        
        return deduped
    
    def _deduplicate_by_title(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Remove duplicates based on title similarity."""
        if not chunks:
            return chunks
        
        # Group chunks by similar titles
        title_groups = defaultdict(list)
        
        for chunk in chunks:
            title = chunk.metadata.title.strip().lower()
            
            # Normalize title for better matching
            normalized_title = self._normalize_title(title)
            
            if not normalized_title:
                title_groups["__empty__"].append(chunk)
                continue
            
            # Check if title is similar to any existing group
            best_group_key = None
            best_similarity = 0.0
            
            for group_key in title_groups.keys():
                if group_key == "__empty__":
                    continue
                
                similarity = self._calculate_title_similarity(normalized_title, group_key)
                
                if similarity > best_similarity and similarity >= 0.85:  # High threshold for titles
                    best_similarity = similarity
                    best_group_key = group_key
            
            if best_group_key:
                title_groups[best_group_key].append(chunk)
            else:
                title_groups[normalized_title].append(chunk)
        
        # Select best chunk from each group
        deduped = []
        for group_key, group_chunks in title_groups.items():
            if len(group_chunks) == 1:
                deduped.append(group_chunks[0])
            else:
                # Select the highest quality chunk from the group
                best_chunk = self._select_best_chunk(group_chunks)
                deduped.append(best_chunk)
                logger.debug(f"Title group '{group_key[:50]}...' had {len(group_chunks)} duplicates")
        
        return deduped
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for better matching."""
        if not title:
            return ""
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(breaking[:\s]*|urgent[:\s]*|update[:\s]*)', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*[^-]*$', '', title)  # Remove " - Source Name" suffix
        
        # Remove extra whitespace and punctuation
        title = re.sub(r'[^\w\s]', ' ', title)
        title = ' '.join(title.split())
        
        return title.lower().strip()
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        if not title1 or not title2:
            return 0.0
        
        if FUZZYWUZZY_AVAILABLE and self.config.use_fuzzy_matching:
            # Use token sort ratio for better handling of word order differences
            return fuzz.token_sort_ratio(title1, title2) / 100.0
        
        elif DIFFLIB_AVAILABLE:
            # Fallback to difflib
            return SequenceMatcher(None, title1, title2).ratio()
        
        else:
            # Simple exact match
            return 1.0 if title1 == title2 else 0.0
    
    def _deduplicate_by_content_hash(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Remove duplicates based on content hash."""
        seen_hashes = set()
        deduped = []
        
        for chunk in chunks:
            content = chunk.processed_content or chunk.content
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduped.append(chunk)
            else:
                logger.debug(f"Duplicate content hash found: {chunk.metadata.url}")
        
        return deduped
    
    def _deduplicate_by_semantic_similarity(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Remove duplicates based on semantic similarity of embeddings."""
        if not self.embedding_manager or not chunks:
            return chunks
        
        # Ensure all chunks have embeddings
        chunks_with_embeddings = [chunk for chunk in chunks if chunk.embedding]
        
        if len(chunks_with_embeddings) != len(chunks):
            logger.warning(f"Some chunks missing embeddings: {len(chunks_with_embeddings)}/{len(chunks)}")
        
        if len(chunks_with_embeddings) < 2:
            return chunks
        
        # Calculate similarity matrix
        embeddings = [chunk.embedding for chunk in chunks_with_embeddings]
        similarity_matrix = self.embedding_manager.calculate_similarity_matrix(embeddings)
        
        # Find duplicate pairs
        duplicates_to_remove = set()
        
        for i in range(len(chunks_with_embeddings)):
            if i in duplicates_to_remove:
                continue
            
            for j in range(i + 1, len(chunks_with_embeddings)):
                if j in duplicates_to_remove:
                    continue
                
                similarity = similarity_matrix[i][j]
                
                if similarity >= self.config.similarity_threshold:
                    # Decide which chunk to keep
                    chunk1 = chunks_with_embeddings[i]
                    chunk2 = chunks_with_embeddings[j]
                    
                    if self._is_chunk_better_quality(chunk1, chunk2):
                        duplicates_to_remove.add(j)
                        logger.debug(f"Semantic duplicate: kept {chunk1.metadata.url}, removed {chunk2.metadata.url}")
                    else:
                        duplicates_to_remove.add(i)
                        logger.debug(f"Semantic duplicate: kept {chunk2.metadata.url}, removed {chunk1.metadata.url}")
                        break  # Move to next i since current i is removed
        
        # Return chunks not marked for removal
        deduped = []
        for i, chunk in enumerate(chunks_with_embeddings):
            if i not in duplicates_to_remove:
                deduped.append(chunk)
        
        # Add back chunks without embeddings
        chunks_without_embeddings = [chunk for chunk in chunks if not chunk.embedding]
        deduped.extend(chunks_without_embeddings)
        
        return deduped
    
    def _deduplicate_by_fuzzy_content(self, chunks: List[ContentChunk]) -> List[ContentChunk]:
        """Final pass using fuzzy content matching."""
        if not self.config.use_fuzzy_matching or len(chunks) < 2:
            return chunks
        
        # Group chunks by content similarity
        content_groups = []
        
        for chunk in chunks:
            content = (chunk.processed_content or chunk.content)[:500]  # First 500 chars for efficiency
            
            # Find best matching group
            best_group_idx = None
            best_similarity = 0.0
            
            for group_idx, group in enumerate(content_groups):
                # Compare with first chunk in group as representative
                representative_content = (group[0].processed_content or group[0].content)[:500]
                
                similarity = self._calculate_content_similarity(content, representative_content)
                
                if similarity > best_similarity and similarity >= self.config.fuzzy_ratio_threshold / 100.0:
                    best_similarity = similarity
                    best_group_idx = group_idx
            
            if best_group_idx is not None:
                content_groups[best_group_idx].append(chunk)
            else:
                content_groups.append([chunk])
        
        # Select best chunk from each group
        deduped = []
        for group in content_groups:
            if len(group) == 1:
                deduped.append(group[0])
            else:
                best_chunk = self._select_best_chunk(group)
                deduped.append(best_chunk)
                logger.debug(f"Fuzzy content group had {len(group)} duplicates")
        
        return deduped
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        if not content1 or not content2:
            return 0.0
        
        if FUZZYWUZZY_AVAILABLE and self.config.use_fuzzy_matching:
            return fuzz.ratio(content1, content2) / 100.0
        
        elif DIFFLIB_AVAILABLE:
            return SequenceMatcher(None, content1, content2).ratio()
        
        else:
            return 1.0 if content1 == content2 else 0.0
    
    def _select_best_chunk(self, chunks: List[ContentChunk]) -> ContentChunk:
        """Select the best quality chunk from a group of duplicates."""
        if len(chunks) == 1:
            return chunks[0]
        
        # Score chunks based on multiple quality factors
        scored_chunks = []
        
        for chunk in chunks:
            score = self._calculate_chunk_quality_score(chunk)
            scored_chunks.append((score, chunk))
        
        # Sort by score (descending) and return best
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return scored_chunks[0][1]
    
    def _calculate_chunk_quality_score(self, chunk: ContentChunk) -> float:
        """Calculate quality score for a chunk."""
        score = 0.0
        
        # Source reliability score
        score += chunk.metadata.source_reliability_score * 0.4
        
        # Content length (longer is generally better, up to a point)
        content_length = len(chunk.processed_content or chunk.content)
        length_score = min(content_length / 1000.0, 1.0)  # Cap at 1000 chars
        score += length_score * 0.2
        
        # Recency (newer is better)
        age_hours = (datetime.utcnow() - chunk.metadata.timestamp).total_seconds() / 3600
        recency_score = max(0.0, 1.0 - age_hours / 24.0)  # Decay over 24 hours
        score += recency_score * 0.2
        
        # Title quality (non-empty, reasonable length)
        title_length = len(chunk.metadata.title.strip())
        if title_length > 10 and title_length < 200:
            score += 0.1
        
        # Author presence
        if chunk.metadata.author:
            score += 0.05
        
        # Image presence
        if chunk.metadata.image_urls:
            score += 0.05
        
        return score
    
    def _is_chunk_better_quality(self, chunk1: ContentChunk, chunk2: ContentChunk) -> bool:
        """Compare two chunks and return True if chunk1 is better quality."""
        score1 = self._calculate_chunk_quality_score(chunk1)
        score2 = self._calculate_chunk_quality_score(chunk2)
        return score1 > score2
    
    def find_duplicates_in_new_chunks(self, new_chunks: List[ContentChunk], 
                                    existing_chunks: List[ContentChunk]) -> Tuple[List[ContentChunk], List[ContentChunk]]:
        """
        Find duplicates between new chunks and existing chunks.
        
        Args:
            new_chunks: Newly received chunks
            existing_chunks: Previously processed chunks
            
        Returns:
            Tuple of (unique_new_chunks, duplicate_new_chunks)
        """
        if not new_chunks:
            return [], []
        
        if not existing_chunks:
            return self.deduplicate_chunks(new_chunks), []
        
        logger.info(f"Checking {len(new_chunks)} new chunks against {len(existing_chunks)} existing chunks")
        
        unique_chunks = []
        duplicate_chunks = []
        
        for new_chunk in new_chunks:
            is_duplicate = False
            
            # Check against existing chunks
            for existing_chunk in existing_chunks:
                if self._are_chunks_duplicates(new_chunk, existing_chunk):
                    duplicate_chunks.append(new_chunk)
                    is_duplicate = True
                    logger.debug(f"Found duplicate: {new_chunk.metadata.url}")
                    break
            
            if not is_duplicate:
                unique_chunks.append(new_chunk)
        
        # Deduplicate among the unique new chunks
        final_unique = self.deduplicate_chunks(unique_chunks)
        
        logger.info(f"Result: {len(final_unique)} unique, {len(duplicate_chunks)} duplicates")
        return final_unique, duplicate_chunks
    
    def _are_chunks_duplicates(self, chunk1: ContentChunk, chunk2: ContentChunk) -> bool:
        """Check if two chunks are duplicates using multiple criteria."""
        # URL match
        if chunk1.metadata.url == chunk2.metadata.url:
            return True
        
        # Title similarity
        title_sim = self._calculate_title_similarity(
            self._normalize_title(chunk1.metadata.title),
            self._normalize_title(chunk2.metadata.title)
        )
        if title_sim >= 0.9:
            return True
        
        # Content hash match
        content1 = chunk1.processed_content or chunk1.content
        content2 = chunk2.processed_content or chunk2.content
        
        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()
        
        if hash1 == hash2:
            return True
        
        # Semantic similarity (if embeddings available)
        if (self.embedding_manager and chunk1.embedding and chunk2.embedding):
            semantic_sim = self.embedding_manager.calculate_similarity(
                chunk1.embedding, chunk2.embedding
            )
            if semantic_sim >= self.config.similarity_threshold:
                return True
        
        # Fuzzy content similarity
        if self.config.use_fuzzy_matching:
            content_sim = self._calculate_content_similarity(content1[:500], content2[:500])
            if content_sim >= self.config.fuzzy_ratio_threshold / 100.0:
                return True
        
        return False
    
    def get_duplicate_groups(self, chunks: List[ContentChunk]) -> List[List[ContentChunk]]:
        """
        Group chunks by duplicates without removing them.
        
        Args:
            chunks: List of chunks to group
            
        Returns:
            List of lists, where each inner list contains duplicate chunks
        """
        if not chunks:
            return []
        
        groups = []
        processed = set()
        
        for i, chunk1 in enumerate(chunks):
            if i in processed:
                continue
            
            # Start new group
            group = [chunk1]
            processed.add(i)
            
            # Find all duplicates of this chunk
            for j, chunk2 in enumerate(chunks[i + 1:], i + 1):
                if j in processed:
                    continue
                
                if self._are_chunks_duplicates(chunk1, chunk2):
                    group.append(chunk2)
                    processed.add(j)
            
            groups.append(group)
        
        return groups
    
    def get_deduplication_stats(self, original_chunks: List[ContentChunk], 
                              deduped_chunks: List[ContentChunk]) -> Dict[str, Any]:
        """
        Get statistics about the deduplication process.
        
        Args:
            original_chunks: Original chunk list
            deduped_chunks: Deduplicated chunk list
            
        Returns:
            Dictionary of deduplication statistics
        """
        original_count = len(original_chunks)
        deduped_count = len(deduped_chunks)
        removed_count = original_count - deduped_count
        
        # Calculate by source
        source_stats = defaultdict(lambda: {'original': 0, 'kept': 0, 'removed': 0})
        
        for chunk in original_chunks:
            source = chunk.metadata.source
            source_stats[source]['original'] += 1
        
        for chunk in deduped_chunks:
            source = chunk.metadata.source
            source_stats[source]['kept'] += 1
        
        for source_data in source_stats.values():
            source_data['removed'] = source_data['original'] - source_data['kept']
        
        return {
            'original_count': original_count,
            'deduplicated_count': deduped_count,
            'removed_count': removed_count,
            'removal_percentage': (removed_count / original_count * 100) if original_count > 0 else 0,
            'source_breakdown': dict(source_stats)
        }
    
    def _clear_caches(self):
        """Clear internal caches."""
        self.url_cache.clear()
        self.title_hashes.clear()
        self.content_hashes.clear()
