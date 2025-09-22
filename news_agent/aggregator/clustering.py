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

# Removed HDBSCAN and DBSCAN imports as they will no longer be used
# try:
#     from hdbscan import HDBSCAN
#     HDBSCAN_AVAILABLE = True
# except ImportError:
#     HDBSCAN_AVAILABLE = False

# try:
#     from sklearn.cluster import DBSCAN
#     from sklearn.metrics import silhouette_score
#     SKLEARN_AVAILABLE = True
# except ImportError:
#     SKLEARN_AVAILABLE = False

from .models import ContentChunk, ContentCluster, ClusterMetadata, SourceType
from .config import ClusteringConfig
from .embeddings import EmbeddingManager
from news_agent.aggregator.agentic_clustering.agents import ProposerAgent, EvaluatorAgent, RefinerAgent, AgenticClusteringConfig
from langchain_google_genai import ChatGoogleGenerativeAI # Assuming LLM is Gemini

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """
    Semantic clustering engine using an agentic approach for news content.
    
    Features:
    - Multi-agent based clustering (Proposer, Evaluator, Refiner)
    - Dynamic cluster management
    - Real-time cluster updates
    - Cluster quality assessment using LLM reasoning
    """
    
    def __init__(self, config: ClusteringConfig, embedding_manager: EmbeddingManager, llm: ChatGoogleGenerativeAI):
        """
        Initialize the clustering engine.
        
        Args:
            config: Clustering configuration (will be converted to AgenticClusteringConfig)
            embedding_manager: Embedding manager instance
            llm: Language Model instance for agentic reasoning
        """
        self.config = config
        self.embedding_manager = embedding_manager
        self.llm = llm
        self.active_clusters = {}  # cluster_id -> ContentCluster
        self.cluster_history = []  # For tracking cluster evolution
        
        # Convert generic ClusteringConfig to AgenticClusteringConfig
        self.agentic_config = AgenticClusteringConfig(
            max_iterations=10, # Default, can be made configurable
            initial_grouping_threshold=self.config.similarity_threshold,
            proposer_agent_prompt="You are a Proposer Agent. Your task is to identify initial groupings of news content chunks based on their semantic similarity. Group related chunks into clusters. Output a list of proposed clusters and any unassigned chunks.",
            evaluator_agent_prompt="You are an Evaluator Agent. Your task is to assess the quality of a given news content cluster. Consider its coherence, topic focus, and potential for refinement (splitting or merging). Respond with 'refine' if it needs refinement, otherwise 'good'. Cluster Summary: {cluster_summary}",
            refiner_agent_prompt="You are a Refiner Agent. Your task is to refine existing news content clusters based on evaluation feedback. You can merge similar clusters, split large or incoherent clusters, or reassign chunks. Output the refined clusters and any newly unassigned chunks.",
            min_cluster_size=self.config.min_cluster_size,
            max_cluster_size=self.config.max_cluster_size,
            similarity_metric=self.config.metric # Assuming metric is compatible
        )
        
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize the clustering agents."""
        self.proposer_agent = ProposerAgent(self.agentic_config, self.embedding_manager, self.llm)
        self.evaluator_agent = EvaluatorAgent(self.agentic_config, self.embedding_manager, self.llm)
        self.refiner_agent = RefinerAgent(self.agentic_config, self.embedding_manager, self.llm)
        logger.info("Agentic clustering agents initialized")
    
    def cluster_chunks(self, chunks: List[ContentChunk]) -> List[ContentCluster]:
        """
        Perform agentic clustering on content chunks.
        
        Args:
            chunks: List of ContentChunk objects with embeddings
            
        Returns:
            List of ContentCluster objects
        """
        if not chunks:
            return []
        
        valid_chunks = [chunk for chunk in chunks if chunk.embedding and len(chunk.embedding) > 0]
        if len(valid_chunks) < self.agentic_config.min_cluster_size:
            logger.warning(f"Not enough valid chunks for clustering: {len(valid_chunks)}")
            return []
        
        logger.info(f"Starting agentic clustering for {len(valid_chunks)} chunks.")
        
        current_clusters: List[ContentCluster] = []
        unassigned_chunks: List[ContentChunk] = valid_chunks
        
        for iteration in range(self.agentic_config.max_iterations):
            logger.info(f"Agentic Clustering Iteration {iteration + 1}/{self.agentic_config.max_iterations}")
            
            # 1. Proposer Agent: Propose new clusters from unassigned chunks
            if unassigned_chunks:
                newly_proposed_clusters, remaining_unassigned = self.proposer_agent.propose_clusters(unassigned_chunks)
                current_clusters.extend(newly_proposed_clusters)
                unassigned_chunks = remaining_unassigned
                logger.info(f"Proposer Agent proposed {len(newly_proposed_clusters)} new clusters. {len(unassigned_chunks)} chunks still unassigned.")
            
            if not current_clusters:
                logger.info("No clusters formed yet. Ending iteration.")
                break

            # 2. Evaluator Agent: Evaluate all current clusters
            evaluations = self.evaluator_agent.evaluate_clusters(current_clusters)
            
            # Check if any clusters need refinement
            needs_refinement = any(e.get("needs_refinement", False) for e in evaluations.values())
            if not needs_refinement and not unassigned_chunks:
                logger.info("All clusters evaluated as good and no unassigned chunks. Ending refinement.")
                break
            
            # 3. Refiner Agent: Refine clusters based on evaluations
            refined_clusters, newly_unassigned_from_refinement = self.refiner_agent.refine_clusters(current_clusters, evaluations)
            current_clusters = refined_clusters
            unassigned_chunks.extend(newly_unassigned_from_refinement)
            
            logger.info(f"Refiner Agent produced {len(current_clusters)} clusters. {len(unassigned_chunks)} chunks now unassigned after refinement.")
            
        logger.info(f"Agentic clustering finished after {iteration + 1} iterations. Final {len(current_clusters)} clusters.")
        return current_clusters
    
    # The following methods will be adapted or removed as they are now handled by agents
    # _process_cluster_results is no longer directly used by cluster_chunks
    # update_clusters_with_new_chunks will be replaced by agentic logic
    # merge_similar_clusters will be replaced by agentic logic
    # split_large_clusters will be replaced by agentic logic
    
    # Keep _create_cluster_metadata and _calculate_cluster_coherence as helper methods for agents
    # These are already copied into BaseAgent, so they can be removed from here.
    
    # For now, commenting out the old methods. They will be removed in a later step.
    # def _process_cluster_results(self, chunks: List[ContentChunk], labels: np.ndarray,
    #                            embeddings: np.ndarray) -> List[ContentCluster]:
    #     ... (old implementation) ...
    
    # def update_clusters_with_new_chunks(self, new_chunks: List[ContentChunk],
    #                                   existing_clusters: List[ContentCluster],
    #                                   similarity_threshold: Optional[float] = None) -> Tuple[List[ContentCluster], List[ContentChunk]]:
    #     ... (old implementation) ...
    
    # def create_clusters_from_unassigned(self, unassigned_chunks: List[ContentChunk]) -> List[ContentCluster]:
    #     ... (old implementation) ...
    
    # def merge_similar_clusters(self, clusters: List[ContentCluster],
    #                          similarity_threshold: Optional[float] = None) -> List[ContentCluster]:
    #     ... (old implementation) ...
    
    # def split_large_clusters(self, clusters: List[ContentCluster]) -> List[ContentCluster]:
    #     ... (old implementation) ...
    
    def evaluate_clustering_quality(self, clusters: List[ContentCluster]) -> Dict[str, float]:
        """
        Evaluate the quality of clustering results using agentic evaluations.
        This method will be adapted to use the EvaluatorAgent's insights.
        """
        if not clusters:
            return {}
        
        # Use the EvaluatorAgent to get evaluations
        agent_evaluations = self.evaluator_agent.evaluate_clusters(clusters)
        
        # Aggregate agent evaluations into a single quality metric
        total_coherence = sum(e.get("coherence_score", 0.0) for e in agent_evaluations.values())
        avg_coherence = total_coherence / len(clusters) if clusters else 0.0
        
        num_needs_refinement = sum(1 for e in agent_evaluations.values() if e.get("needs_refinement", False))
        
        sizes = [cluster.chunk_count for cluster in clusters]
        avg_size = np.mean(sizes) if sizes else 0.0
        size_std = np.std(sizes) if sizes else 0.0
        
        return {
            'average_coherence': float(avg_coherence),
            'num_clusters': len(clusters),
            'average_cluster_size': float(avg_size),
            'cluster_size_std': float(size_std),
            'total_chunks': sum(sizes),
            'num_clusters_needing_refinement': num_needs_refinement
        }
    
    def get_cluster_summary_stats(self, clusters: List[ContentCluster]) -> Dict[str, Any]:
        """
        Get summary statistics for clusters.
        (This method can remain largely the same, as it's descriptive)
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
            'min_cluster_size': min(sizes) if sizes else 0,
            'max_cluster_size': max(sizes) if sizes else 0,
            'avg_cluster_size': float(np.mean(sizes)) if sizes else 0.0,
            'median_cluster_size': float(np.median(sizes)) if sizes else 0.0,
            'unique_topics': len(topics),
            'unique_tickers': len(tickers),
            'unique_source_types': len(source_types),
            'topics': list(topics),
            'tickers': list(tickers),
            'source_types': [st.value for st in source_types]
        }
