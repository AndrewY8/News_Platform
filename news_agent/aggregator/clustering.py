"""
Semantic clustering pipeline using HDBSCAN for the News Aggregator.

This module provides density-based clustering of news content using
semantic embeddings, with support for dynamic cluster management
and real-time cluster updates.
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from hdbscan import HDBSCAN
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

try:
    from sklearn.cluster import DBSCAN
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .models import ContentChunk, ContentCluster, ClusterMetadata, SourceType
from .config import ClusteringConfig
from .embeddings import EmbeddingManager

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """
    Semantic clustering engine using HDBSCAN for news content.
    
    Features:
    - HDBSCAN-based density clustering
    - Dynamic cluster management
    - Real-time cluster updates
    - Cluster quality assessment
    - Multi-level clustering (hierarchical)
    """
    
    def __init__(self, config: ClusteringConfig, embedding_manager: EmbeddingManager):
        """
        Initialize the clustering engine.
        
        Args:
            config: Clustering configuration
            embedding_manager: Embedding manager instance
        """
        self.config = config
        self.embedding_manager = embedding_manager
        self.active_clusters = {}  # cluster_id -> ContentCluster
        self.cluster_history = []  # For tracking cluster evolution
        
        if not HDBSCAN_AVAILABLE and not SKLEARN_AVAILABLE:
            raise ImportError("Either hdbscan or scikit-learn is required for clustering")
        
        self._initialize_clusterer()
    
    def _initialize_clusterer(self):
        """Initialize the clustering algorithm."""
        if HDBSCAN_AVAILABLE:
            self.clusterer = HDBSCAN(
                min_cluster_size=self.config.min_cluster_size,
                min_samples=self.config.min_samples,
                metric=self.config.metric,
                cluster_selection_method=self.config.cluster_selection_method,
                cluster_selection_epsilon=self.config.cluster_selection_epsilon,
                alpha=self.config.alpha
            )
            self.clustering_method = "hdbscan"
            logger.info("HDBSCAN clusterer initialized")
        
        elif SKLEARN_AVAILABLE:
            # Fallback to DBSCAN
            eps = 1.0 - self.config.similarity_threshold  # Convert similarity to distance
            self.clusterer = DBSCAN(
                eps=eps,
                min_samples=self.config.min_samples,
                metric='cosine'
            )
            self.clustering_method = "dbscan"
            logger.info("DBSCAN clusterer initialized (fallback)")
        
        else:
            raise ImportError("No clustering algorithm available")
    
    def cluster_chunks(self, chunks: List[ContentChunk]) -> List[ContentCluster]:
        """
        Perform clustering on content chunks.
        
        Args:
            chunks: List of ContentChunk objects with embeddings
            
        Returns:
            List of ContentCluster objects
        """
        if not chunks:
            return []
        
        # Filter chunks with valid embeddings
        valid_chunks = [chunk for chunk in chunks if chunk.embedding and len(chunk.embedding) > 0]
        
        if len(valid_chunks) < self.config.min_cluster_size:
            logger.warning(f"Not enough valid chunks for clustering: {len(valid_chunks)}")
            return []
        
        logger.info(f"Clustering {len(valid_chunks)} chunks using {self.clustering_method}")
        
        # Extract embeddings
        embeddings = np.array([chunk.embedding for chunk in valid_chunks])
        
        # Perform clustering
        try:
            cluster_labels = self.clusterer.fit_predict(embeddings)
            
            # Process results
            clusters = self._process_cluster_results(valid_chunks, cluster_labels, embeddings)
            
            logger.info(f"Created {len(clusters)} clusters from {len(valid_chunks)} chunks")
            return clusters
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return []
    
    def _process_cluster_results(self, chunks: List[ContentChunk], labels: np.ndarray, 
                               embeddings: np.ndarray) -> List[ContentCluster]:
        """
        Process clustering results into ContentCluster objects.
        
        Args:
            chunks: Original chunks
            labels: Cluster labels from clustering algorithm
            embeddings: Embedding vectors
            
        Returns:
            List of ContentCluster objects
        """
        clusters = []
        cluster_groups = defaultdict(list)
        
        # Group chunks by cluster label
        for chunk, label in zip(chunks, labels):
            if label != -1:  # -1 indicates noise/outliers
                chunk.cluster_id = f"cluster_{label}"
                cluster_groups[label].append(chunk)
        
        # Create ContentCluster objects
        for cluster_id, cluster_chunks in cluster_groups.items():
            # Skip clusters that are too small
            if len(cluster_chunks) < self.config.min_cluster_size:
                continue
            
            # Skip clusters that are too large (might indicate poor clustering)
            if len(cluster_chunks) > self.config.max_cluster_size:
                logger.warning(f"Cluster {cluster_id} is very large: {len(cluster_chunks)} chunks")
                # Could split large clusters here if needed
                continue
            
            # Calculate cluster centroid
            cluster_embeddings = [chunk.embedding for chunk in cluster_chunks]
            centroid = self.embedding_manager.compute_centroid(cluster_embeddings)
            
            # Create cluster metadata
            metadata = self._create_cluster_metadata(cluster_chunks)
            
            # Create cluster object
            cluster = ContentCluster(
                id=f"cluster_{cluster_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                chunks=cluster_chunks,
                centroid=centroid,
                metadata=metadata
            )
            
            clusters.append(cluster)
        
        return clusters
    
    def _create_cluster_metadata(self, chunks: List[ContentChunk]) -> ClusterMetadata:
        """
        Create metadata for a cluster based on its chunks.
        
        Args:
            chunks: List of chunks in the cluster
            
        Returns:
            ClusterMetadata object
        """
        # Extract topics
        topics = set()
        tickers = set()
        source_types = set()
        timestamps = []
        
        for chunk in chunks:
            if chunk.metadata.topic:
                topics.add(chunk.metadata.topic)
            if chunk.metadata.ticker:
                tickers.add(chunk.metadata.ticker)
            source_types.add(chunk.metadata.source_type)
            timestamps.append(chunk.metadata.timestamp)
        
        # Determine primary ticker (most common)
        primary_ticker = None
        if tickers:
            ticker_counts = {ticker: sum(1 for chunk in chunks if chunk.metadata.ticker == ticker) 
                           for ticker in tickers}
            primary_ticker = max(ticker_counts.items(), key=lambda x: x[1])[0]
        
        # Calculate time range
        time_range = None
        if timestamps:
            time_range = (min(timestamps), max(timestamps))
        
        # Calculate cluster coherence score
        confidence_score = self._calculate_cluster_coherence(chunks)
        
        return ClusterMetadata(
            primary_ticker=primary_ticker,
            topics=list(topics),
            time_range=time_range,
            source_types=list(source_types),
            confidence_score=confidence_score,
            cluster_size=len(chunks)
        )
    
    def _calculate_cluster_coherence(self, chunks: List[ContentChunk]) -> float:
        """
        Calculate a coherence score for a cluster based on internal similarity.
        
        Args:
            chunks: List of chunks in the cluster
            
        Returns:
            Coherence score between 0 and 1
        """
        if len(chunks) < 2:
            return 1.0
        
        try:
            embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
            if len(embeddings) < 2:
                return 0.5
            
            # Calculate pairwise similarities within cluster
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = self.embedding_manager.calculate_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)
            
            # Return average internal similarity
            return np.mean(similarities) if similarities else 0.5
            
        except Exception as e:
            logger.warning(f"Failed to calculate cluster coherence: {e}")
            return 0.5
    
    def update_clusters_with_new_chunks(self, new_chunks: List[ContentChunk], 
                                      existing_clusters: List[ContentCluster],
                                      similarity_threshold: Optional[float] = None) -> Tuple[List[ContentCluster], List[ContentChunk]]:
        """
        Update existing clusters with new chunks or create new clusters.
        
        Args:
            new_chunks: New chunks to cluster
            existing_clusters: Existing clusters to update
            similarity_threshold: Threshold for assigning to existing clusters
            
        Returns:
            Tuple of (updated_clusters, unassigned_chunks)
        """
        if not new_chunks:
            return existing_clusters, []
        
        threshold = similarity_threshold or self.config.similarity_threshold
        updated_clusters = existing_clusters.copy()
        unassigned_chunks = []
        
        logger.info(f"Updating clusters with {len(new_chunks)} new chunks")
        
        for chunk in new_chunks:
            if not chunk.embedding:
                unassigned_chunks.append(chunk)
                continue
            
            best_cluster = None
            best_similarity = 0.0
            
            # Find best matching existing cluster
            for cluster in updated_clusters:
                if not cluster.centroid:
                    continue
                
                similarity = self.embedding_manager.calculate_similarity(
                    chunk.embedding, cluster.centroid
                )
                
                if similarity > best_similarity and similarity >= threshold:
                    best_similarity = similarity
                    best_cluster = cluster
            
            if best_cluster:
                # Add chunk to existing cluster
                chunk.cluster_id = best_cluster.id
                best_cluster.chunks.append(chunk)
                
                # Update cluster centroid
                cluster_embeddings = [c.embedding for c in best_cluster.chunks if c.embedding]
                best_cluster.centroid = self.embedding_manager.compute_centroid(cluster_embeddings)
                
                # Update metadata
                best_cluster.metadata = self._create_cluster_metadata(best_cluster.chunks)
                best_cluster.updated_at = datetime.utcnow()
                
                logger.debug(f"Added chunk {chunk.id} to cluster {best_cluster.id}")
            else:
                unassigned_chunks.append(chunk)
        
        logger.info(f"Assigned {len(new_chunks) - len(unassigned_chunks)} chunks to existing clusters")
        logger.info(f"{len(unassigned_chunks)} chunks remain unassigned")
        
        return updated_clusters, unassigned_chunks
    
    def create_clusters_from_unassigned(self, unassigned_chunks: List[ContentChunk]) -> List[ContentCluster]:
        """
        Create new clusters from unassigned chunks.
        
        Args:
            unassigned_chunks: Chunks not assigned to existing clusters
            
        Returns:
            List of new ContentCluster objects
        """
        if len(unassigned_chunks) < self.config.min_cluster_size:
            logger.info(f"Not enough unassigned chunks for new clusters: {len(unassigned_chunks)}")
            return []
        
        return self.cluster_chunks(unassigned_chunks)
    
    def merge_similar_clusters(self, clusters: List[ContentCluster], 
                             similarity_threshold: Optional[float] = None) -> List[ContentCluster]:
        """
        Merge clusters that are very similar to each other.
        
        Args:
            clusters: List of clusters to potentially merge
            similarity_threshold: Threshold for merging clusters
            
        Returns:
            List of clusters after merging
        """
        if len(clusters) < 2:
            return clusters
        
        threshold = similarity_threshold or self.config.similarity_threshold
        merged_clusters = clusters.copy()
        
        logger.info(f"Checking for similar clusters to merge (threshold: {threshold})")
        
        # Calculate pairwise similarities between cluster centroids
        centroids = [cluster.centroid for cluster in merged_clusters if cluster.centroid]
        if len(centroids) < 2:
            return merged_clusters
        
        similarity_matrix = self.embedding_manager.calculate_similarity_matrix(centroids)
        
        # Find pairs of clusters to merge
        merges_made = True
        while merges_made and len(merged_clusters) > 1:
            merges_made = False
            
            for i in range(len(merged_clusters)):
                for j in range(i + 1, len(merged_clusters)):
                    if i >= len(merged_clusters) or j >= len(merged_clusters):
                        continue
                    
                    cluster1 = merged_clusters[i]
                    cluster2 = merged_clusters[j]
                    
                    if not cluster1.centroid or not cluster2.centroid:
                        continue
                    
                    similarity = self.embedding_manager.calculate_similarity(
                        cluster1.centroid, cluster2.centroid
                    )
                    
                    if similarity >= threshold:
                        # Merge clusters
                        logger.info(f"Merging clusters {cluster1.id} and {cluster2.id} (similarity: {similarity:.3f})")
                        
                        # Combine chunks
                        combined_chunks = cluster1.chunks + cluster2.chunks
                        
                        # Update cluster IDs for all chunks
                        new_cluster_id = f"merged_{cluster1.id}_{cluster2.id}"
                        for chunk in combined_chunks:
                            chunk.cluster_id = new_cluster_id
                        
                        # Create merged cluster
                        combined_embeddings = [c.embedding for c in combined_chunks if c.embedding]
                        new_centroid = self.embedding_manager.compute_centroid(combined_embeddings)
                        new_metadata = self._create_cluster_metadata(combined_chunks)
                        
                        merged_cluster = ContentCluster(
                            id=new_cluster_id,
                            chunks=combined_chunks,
                            centroid=new_centroid,
                            metadata=new_metadata,
                            created_at=min(cluster1.created_at, cluster2.created_at),
                            updated_at=datetime.utcnow()
                        )
                        
                        # Replace original clusters with merged cluster
                        merged_clusters = [c for k, c in enumerate(merged_clusters) 
                                         if k not in [i, j]] + [merged_cluster]
                        merges_made = True
                        break
                
                if merges_made:
                    break
        
        logger.info(f"Cluster merging completed: {len(clusters)} -> {len(merged_clusters)} clusters")
        return merged_clusters
    
    def split_large_clusters(self, clusters: List[ContentCluster]) -> List[ContentCluster]:
        """
        Split clusters that are too large into smaller sub-clusters.
        
        Args:
            clusters: List of clusters to potentially split
            
        Returns:
            List of clusters after splitting
        """
        result_clusters = []
        
        for cluster in clusters:
            if cluster.chunk_count <= self.config.max_cluster_size:
                result_clusters.append(cluster)
                continue
            
            logger.info(f"Splitting large cluster {cluster.id} with {cluster.chunk_count} chunks")
            
            # Re-cluster the chunks in this large cluster with stricter parameters
            sub_config = ClusteringConfig(
                min_cluster_size=max(2, self.config.min_cluster_size // 2),
                min_samples=max(1, self.config.min_samples // 2),
                similarity_threshold=self.config.similarity_threshold + 0.1,  # More strict
                max_cluster_size=self.config.max_cluster_size // 2
            )
            
            sub_engine = ClusteringEngine(sub_config, self.embedding_manager)
            sub_clusters = sub_engine.cluster_chunks(cluster.chunks)
            
            if sub_clusters:
                result_clusters.extend(sub_clusters)
                logger.info(f"Split cluster into {len(sub_clusters)} sub-clusters")
            else:
                # If splitting failed, keep original cluster
                result_clusters.append(cluster)
        
        return result_clusters
    
    def evaluate_clustering_quality(self, clusters: List[ContentCluster]) -> Dict[str, float]:
        """
        Evaluate the quality of clustering results.
        
        Args:
            clusters: List of clusters to evaluate
            
        Returns:
            Dictionary of quality metrics
        """
        if not clusters or not SKLEARN_AVAILABLE:
            return {}
        
        try:
            # Collect all embeddings and labels
            all_embeddings = []
            all_labels = []
            
            for i, cluster in enumerate(clusters):
                for chunk in cluster.chunks:
                    if chunk.embedding:
                        all_embeddings.append(chunk.embedding)
                        all_labels.append(i)
            
            if len(all_embeddings) < 2 or len(set(all_labels)) < 2:
                return {}
            
            embeddings_array = np.array(all_embeddings)
            labels_array = np.array(all_labels)
            
            # Calculate silhouette score
            silhouette = silhouette_score(embeddings_array, labels_array, metric='cosine')
            
            # Calculate average cluster coherence
            coherence_scores = [cluster.metadata.confidence_score for cluster in clusters 
                              if cluster.metadata.confidence_score is not None]
            avg_coherence = np.mean(coherence_scores) if coherence_scores else 0.0
            
            # Calculate cluster size statistics
            sizes = [cluster.chunk_count for cluster in clusters]
            size_std = np.std(sizes) if sizes else 0.0
            avg_size = np.mean(sizes) if sizes else 0.0
            
            return {
                'silhouette_score': float(silhouette),
                'average_coherence': float(avg_coherence),
                'num_clusters': len(clusters),
                'average_cluster_size': float(avg_size),
                'cluster_size_std': float(size_std),
                'total_chunks': sum(sizes)
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate clustering quality: {e}")
            return {}
    
    def get_cluster_summary_stats(self, clusters: List[ContentCluster]) -> Dict[str, Any]:
        """
        Get summary statistics for clusters.
        
        Args:
            clusters: List of clusters
            
        Returns:
            Dictionary of summary statistics
        """
        if not clusters:
            return {}
        
        sizes = [cluster.chunk_count for cluster in clusters]
        topics = set()
        tickers = set()
        source_types = set()
        
        for cluster in clusters:
            topics.update(cluster.metadata.topics)
            if cluster.metadata.primary_ticker:
                tickers.add(cluster.metadata.primary_ticker)
            source_types.update(cluster.metadata.source_types)
        
        return {
            'num_clusters': len(clusters),
            'total_chunks': sum(sizes),
            'min_cluster_size': min(sizes),
            'max_cluster_size': max(sizes),
            'avg_cluster_size': np.mean(sizes),
            'median_cluster_size': np.median(sizes),
            'unique_topics': len(topics),
            'unique_tickers': len(tickers),
            'unique_source_types': len(source_types),
            'topics': list(topics),
            'tickers': list(tickers),
            'source_types': [st.value for st in source_types]
        }
