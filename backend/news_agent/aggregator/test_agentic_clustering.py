import logging # Added logging import
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta, timezone # Added timezone import
import numpy as np # Added numpy import
from news_agent.aggregator.models import ContentChunk, ChunkMetadata, ContentCluster, SourceType, ReliabilityTier
from news_agent.aggregator.embeddings import EmbeddingManager
from news_agent.aggregator.config import ClusteringConfig
from news_agent.aggregator.agentic_clustering.agents import AgenticClusteringConfig, ProposerAgent, EvaluatorAgent, RefinerAgent
from news_agent.aggregator.clustering import ClusteringEngine
from langchain_core.messages import HumanMessage # Added HumanMessage import
from langchain_core.runnables import Runnable
from langchain_core.prompt_values import ChatPromptValue

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s') # Configure logging
logger = logging.getLogger(__name__)

# Mock LLM for testing purposes
class MockLLM(Runnable):
    def __init__(self):
        pass
    def invoke(self, input_data: dict, config = None) -> HumanMessage:
        # If input is a ChatPromptValue (from a ChatPromptTemplate)
        if isinstance(input_data, ChatPromptValue):
            # Convert to string so we can inspect it
            text = " ".join(m.content for m in input_data.messages)
        # If input is a dict (direct call)
        elif isinstance(input_data, dict):
            text = input_data.get("cluster_summary", "")
        else:
            text = str(input_data)

        logger.debug(f"MockLLM received input text: {text}") # Added debug log
        text_lower = text.lower()

        if "evaluator agent" in text_lower:
            if "large_cluster" in text_lower:
                return HumanMessage(content="refine: Cluster is too large.")
            if "small_cluster" in text_lower:
                return HumanMessage(content="refine: Cluster is too small.")
            if "incoherent_cluster" in text_lower:
                return HumanMessage(content="refine: Potentially diverse topics.")
            return HumanMessage(content="good: Cluster looks coherent.")

        return HumanMessage(content="Mock LLM response.")

def get_mock_llm():
    return MockLLM()

def get_mock_embedding_manager():
    manager = Mock(spec=EmbeddingManager)
    manager.calculate_similarity.side_effect = lambda e1, e2: 1.0 - np.linalg.norm(np.array(e1) - np.array(e2)) / 2.0
    manager.compute_centroid.side_effect = lambda embeddings: np.mean(embeddings, axis=0).tolist()
    manager.calculate_similarity_matrix.side_effect = lambda embeddings: np.array([[manager.calculate_similarity(e1, e2) for e2 in embeddings] for e1 in embeddings])
    return manager


def get_base_clustering_config():
    return ClusteringConfig(
        min_cluster_size=2,
        max_cluster_size=5,
        similarity_threshold=0.7,
        metric="cosine",
        cluster_selection_method="eom",
        cluster_selection_epsilon=0.5,
        alpha=1.0
    )

def get_agentic_clustering_config():
    base_config = get_base_clustering_config()
    return AgenticClusteringConfig(
        max_iterations=3,
        initial_grouping_threshold=base_config.similarity_threshold,
        proposer_agent_prompt="You are a Proposer Agent. Your task is to identify initial groupings of news content chunks based on their semantic similarity. Group related chunks into clusters. Output a list of proposed clusters and any unassigned chunks.",
        evaluator_agent_prompt="You are an Evaluator Agent. Your task is to assess the quality of a given news content cluster. Consider its coherence, topic focus, and potential for refinement (splitting or merging). Respond with 'refine' if it needs refinement, otherwise 'good'. Cluster Summary: {cluster_summary}",
        refiner_agent_prompt="You are a Refiner Agent. Your task is to refine existing news content clusters based on evaluation feedback. You can merge similar clusters, split large or incoherent clusters, or reassign chunks. Output the refined clusters and any newly unassigned chunks.",
        min_cluster_size=base_config.min_cluster_size,
        max_cluster_size=base_config.max_cluster_size,
        similarity_metric=base_config.metric
    )

def get_sample_chunks():
    metadata1 = ChunkMetadata(
        timestamp=datetime.now(timezone.utc), source="SourceA", url="http://a.com", title="Title A",
        topic="Topic1", source_type=SourceType.GENERAL_NEWS, reliability_tier=ReliabilityTier.TIER_3,
        source_retriever="test"
    )
    metadata2 = ChunkMetadata(
        timestamp=datetime.now(timezone.utc), source="SourceA", url="http://a.com/2", title="Title A2",
        topic="Topic1", source_type=SourceType.GENERAL_NEWS, reliability_tier=ReliabilityTier.TIER_3,
        source_retriever="test"
    )
    metadata3 = ChunkMetadata(
        timestamp=datetime.now(timezone.utc), source="SourceB", url="http://b.com", title="Title B",
        topic="Topic2", source_type=SourceType.FINANCIAL_NEWS, reliability_tier=ReliabilityTier.TIER_2,
        source_retriever="test"
    )
    metadata4 = ChunkMetadata(
        timestamp=datetime.now(timezone.utc), source="SourceB", url="http://b.com/2", title="Title B2",
        topic="Topic2", source_type=SourceType.FINANCIAL_NEWS, reliability_tier=ReliabilityTier.TIER_2,
        source_retriever="test"
    )
    metadata5 = ChunkMetadata(
        timestamp=datetime.now(timezone.utc), source="SourceC", url="http://c.com", title="Title C",
        topic="Topic3", source_type=SourceType.BREAKING_NEWS, reliability_tier=ReliabilityTier.TIER_1,
        source_retriever="test"
    )

    chunk1 = ContentChunk(id="1", content="Content A", metadata=metadata1, embedding=[0.1, 0.1, 0.1])
    chunk2 = ContentChunk(id="2", content="Content A related", metadata=metadata2, embedding=[0.15, 0.1, 0.1])
    chunk3 = ContentChunk(id="3", content="Content B", metadata=metadata3, embedding=[0.8, 0.8, 0.8])
    chunk4 = ContentChunk(id="4", content="Content B related", metadata=metadata4, embedding=[0.85, 0.8, 0.8])
    chunk5 = ContentChunk(id="5", content="Content C unique", metadata=metadata5, embedding=[0.5, 0.5, 0.5])
    
    return [chunk1, chunk2, chunk3, chunk4, chunk5]

def run_tests():
    mock_embedding_manager_instance = get_mock_embedding_manager()
    mock_llm_instance = get_mock_llm()
    base_clustering_config_instance = get_base_clustering_config()
    agentic_clustering_config_instance = get_agentic_clustering_config()
    sample_chunks_instance = get_sample_chunks()

    print("Running ProposerAgent tests...")
    test_propose_clusters_basic(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    test_propose_clusters_not_enough_for_min_size(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance)
    print("ProposerAgent tests passed.")

    print("\nRunning EvaluatorAgent tests...")
    test_evaluate_clusters_good_coherence(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    test_evaluate_clusters_needs_refinement_low_coherence(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    test_evaluate_clusters_needs_refinement_llm_feedback(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    print("EvaluatorAgent tests passed.")

    print("\nRunning RefinerAgent tests...")
    test_refine_clusters_split_large(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    test_refine_clusters_disband_small(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    test_refine_clusters_merge_similar(mock_embedding_manager_instance, mock_llm_instance, agentic_clustering_config_instance, sample_chunks_instance)
    print("RefinerAgent tests passed.")

    print("\nRunning ClusteringEngineAgentic tests...")
    test_agentic_clustering_pipeline(base_clustering_config_instance, mock_embedding_manager_instance, mock_llm_instance, sample_chunks_instance)
    test_evaluate_clustering_quality_agentic(base_clustering_config_instance, mock_embedding_manager_instance, mock_llm_instance, sample_chunks_instance)
    print("ClusteringEngineAgentic tests passed.")

def test_propose_clusters_basic(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = ProposerAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    clusters, unassigned = agent.propose_clusters(sample_chunks)
    
    assert len(clusters) >= 1, "Should propose at least one cluster"
    assert all(len(c.chunks) >= agentic_clustering_config.min_cluster_size for c in clusters), "All clusters should meet min_cluster_size"
    
    # Check if chunks with similar embeddings are clustered
    # This part needs to be more robust for direct execution without pytest's context
    # For now, a basic check
    assert any(chunk.id in [c.id for c in clusters[0].chunks] for chunk in sample_chunks[:2]), "Chunks 1 and 2 should be in a cluster"
    assert any(chunk.id in [c.id for c in clusters[1].chunks] for chunk in sample_chunks[2:4]), "Chunks 3 and 4 should be in a cluster"

def test_propose_clusters_not_enough_for_min_size(mock_embedding_manager, mock_llm, agentic_clustering_config):
    metadata = ChunkMetadata(
        timestamp=datetime.now(timezone.utc), source="SourceX", url="http://x.com", title="Title X",
        topic="TopicX", source_type=SourceType.GENERAL_NEWS, reliability_tier=ReliabilityTier.TIER_3,
        source_retriever="test"
    )
    single_chunk = [ContentChunk(id="6", content="Single", metadata=metadata, embedding=[0.2, 0.2, 0.2])]
    
    agent = ProposerAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    clusters, unassigned = agent.propose_clusters(single_chunk)
    
    assert len(clusters) == 0, "No clusters should be formed for single chunk"
    assert len(unassigned) == 1, "Single chunk should be unassigned"
    assert unassigned[0].id == "6", "Unassigned chunk ID mismatch"

def test_evaluate_clusters_good_coherence(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = EvaluatorAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create a coherent cluster
    coherent_chunks = sample_chunks[:2] # chunk1, chunk2
    coherent_cluster = ContentCluster(
        id="coherent_cluster",
        chunks=coherent_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in coherent_chunks]),
        metadata=agent._create_cluster_metadata(coherent_chunks)
    )
    
    evaluations = agent.evaluate_clusters([coherent_cluster])
    assert coherent_cluster.id in evaluations, "Coherent cluster ID not in evaluations"
    assert evaluations[coherent_cluster.id]["coherence_score"] > agentic_clustering_config.initial_grouping_threshold, "Coherence score too low for coherent cluster"
    print("hello")
    print(evaluations[coherent_cluster.id]["llm_evaluation"])
    assert "good" in evaluations[coherent_cluster.id]["llm_evaluation"].lower(), "LLM evaluation not 'good' for coherent cluster"
    assert not evaluations[coherent_cluster.id]["needs_refinement"], "Coherent cluster marked for refinement"

def test_evaluate_clusters_needs_refinement_low_coherence(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = EvaluatorAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create a less coherent cluster (e.g., mixing very different chunks)
    incoherent_chunks = [sample_chunks[0], sample_chunks[2]] # chunk1, chunk3
    incoherent_cluster = ContentCluster(
        id="incoherent_cluster",
        chunks=incoherent_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in incoherent_chunks]),
        metadata=agent._create_cluster_metadata(incoherent_chunks)
    )
    
    evaluations = agent.evaluate_clusters([incoherent_cluster])
    assert incoherent_cluster.id in evaluations, "Incoherent cluster ID not in evaluations"
    assert evaluations[incoherent_cluster.id]["coherence_score"] < agentic_clustering_config.initial_grouping_threshold, "Coherence score too high for incoherent cluster"
    assert evaluations[incoherent_cluster.id]["needs_refinement"], "Incoherent cluster not marked for refinement"

def test_evaluate_clusters_needs_refinement_llm_feedback(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = EvaluatorAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create a cluster that LLM would flag (e.g., too large)
    large_chunks = sample_chunks * 20 # Make it large
    large_cluster = ContentCluster(
        id="large_cluster",
        chunks=large_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in large_chunks if c.embedding]),
        metadata=agent._create_cluster_metadata(large_chunks)
    )
    
    evaluations = agent.evaluate_clusters([large_cluster])
    assert large_cluster.id in evaluations, "Large cluster ID not in evaluations"
    assert "refine" in evaluations[large_cluster.id]["llm_evaluation"].lower(), "LLM evaluation not 'refine' for large cluster"
    assert evaluations[large_cluster.id]["needs_refinement"], "Large cluster not marked for refinement"

def test_refine_clusters_split_large(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = RefinerAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create a cluster that is "too large"
    large_chunks = sample_chunks * 20
    large_cluster = ContentCluster(
        id="large_cluster_to_split",
        chunks=large_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in large_chunks if c.embedding]),
        metadata=agent._create_cluster_metadata(large_chunks)
    )
    
    evaluations = {
        large_cluster.id: {
            "coherence_score": 0.8,
            "llm_evaluation": "refine: Cluster is too large, consider splitting.",
            "needs_refinement": True
        }
    }
    
    refined_clusters, unassigned = agent.refine_clusters([large_cluster], evaluations)
    
    # Current _split_cluster implementation disbands large clusters
    assert len(refined_clusters) == 0, "Refined clusters should be empty after splitting large cluster"
    
def test_refine_clusters_disband_small(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = RefinerAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create a cluster that is "too small"
    small_cluster = ContentCluster(
        id="small_cluster_to_disband",
        chunks=[sample_chunks[0]], # Single chunk
        centroid=sample_chunks[0].embedding,
        metadata=agent._create_cluster_metadata([sample_chunks[0]])
    )
    
    evaluations = {
        small_cluster.id: {
            "coherence_score": 1.0,
            "llm_evaluation": "refine: Cluster is too small.",
            "needs_refinement": True
        }
    }
    
    refined_clusters, unassigned = agent.refine_clusters([small_cluster], evaluations)
    
    assert len(refined_clusters) == 0, "Refined clusters should be empty after disbanding small cluster"
    assert len(unassigned) == 1, "Single chunk should be unassigned after disbanding small cluster"
    assert unassigned[0].id == small_cluster.chunks[0].id, "Unassigned chunk ID mismatch after disbanding small cluster"

def test_refine_clusters_merge_similar(mock_embedding_manager, mock_llm, agentic_clustering_config, sample_chunks):
    agent = RefinerAgent(agentic_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create two similar clusters
    cluster1_chunks = sample_chunks[:2]
    cluster2_chunks = sample_chunks[2:4]
    
    # Adjust embeddings to be similar enough for merging
    cluster1_chunks[0].embedding = [0.1, 0.1, 0.1]
    cluster1_chunks[1].embedding = [0.12, 0.1, 0.1]
    cluster2_chunks[0].embedding = [0.11, 0.1, 0.1]
    cluster2_chunks[1].embedding = [0.13, 0.1, 0.1]

    cluster1 = ContentCluster(
        id="merge_cluster_1",
        chunks=cluster1_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in cluster1_chunks]),
        metadata=agent._create_cluster_metadata(cluster1_chunks)
    )
    cluster2 = ContentCluster(
        id="merge_cluster_2",
        chunks=cluster2_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in cluster2_chunks]),
        metadata=agent._create_cluster_metadata(cluster2_chunks)
    )
    
    evaluations = {
        cluster1.id: {"coherence_score": 0.9, "llm_evaluation": "good", "needs_refinement": False},
        cluster2.id: {"coherence_score": 0.9, "llm_evaluation": "good", "needs_refinement": False}
    }
    
    refined_clusters, unassigned = agent.refine_clusters([cluster1, cluster2], evaluations)
    
    assert len(refined_clusters) == 1, "Should merge into one cluster"
    assert len(refined_clusters[0].chunks) == len(cluster1_chunks) + len(cluster2_chunks), "Merged cluster should contain all chunks"
    assert len(unassigned) == 0, "No chunks should be unassigned after merge"

def test_agentic_clustering_pipeline(base_clustering_config, mock_embedding_manager, mock_llm, sample_chunks):
    engine = ClusteringEngine(base_clustering_config, mock_embedding_manager, mock_llm)
    
    # Ensure agents are initialized
    assert isinstance(engine.proposer_agent, ProposerAgent), "ProposerAgent not initialized"
    assert isinstance(engine.evaluator_agent, EvaluatorAgent), "EvaluatorAgent not initialized"
    assert isinstance(engine.refiner_agent, RefinerAgent), "RefinerAgent not initialized"
    
    final_clusters = engine.cluster_chunks(sample_chunks)
    
    # Expect some clusters to be formed
    assert len(final_clusters) >= 1, "Expected at least one cluster to be formed"
    
    # Check if chunks are assigned to clusters
    all_assigned_chunk_ids = set()
    for cluster in final_clusters:
        for chunk in cluster.chunks:
            all_assigned_chunk_ids.add(chunk.id)
    
    # At least some chunks should be clustered
    assert len(all_assigned_chunk_ids) > 0, "Expected some chunks to be assigned to clusters"
    
    # Verify that the old HDBSCAN/DBSCAN methods are not used
    # (This is implicitly tested by the fact that _initialize_clusterer is replaced)
    
def test_evaluate_clustering_quality_agentic(base_clustering_config, mock_embedding_manager, mock_llm, sample_chunks):
    engine = ClusteringEngine(base_clustering_config, mock_embedding_manager, mock_llm)
    
    # Create some clusters for evaluation
    cluster1_chunks = sample_chunks[:2]
    cluster2_chunks = sample_chunks[2:4]
    
    cluster1 = ContentCluster(
        id="eval_cluster_1",
        chunks=cluster1_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in cluster1_chunks]),
        metadata=engine.proposer_agent._create_cluster_metadata(cluster1_chunks)
    )
    cluster2 = ContentCluster(
        id="eval_cluster_2",
        chunks=cluster2_chunks,
        centroid=mock_embedding_manager.compute_centroid([c.embedding for c in cluster2_chunks]),
        metadata=engine.proposer_agent._create_cluster_metadata(cluster2_chunks)
    )
    
    clusters_to_evaluate = [cluster1, cluster2]
    
    quality_metrics = engine.evaluate_clustering_quality(clusters_to_evaluate)
    
    assert "average_coherence" in quality_metrics, "average_coherence not in quality metrics"
    assert "num_clusters" in quality_metrics, "num_clusters not in quality metrics"
    assert "num_clusters_needing_refinement" in quality_metrics, "num_clusters_needing_refinement not in quality metrics"
    assert quality_metrics["num_clusters"] == 2, "Expected 2 clusters in quality metrics"
    # Based on mock LLM, these should be 'good' so no refinement needed
    assert quality_metrics["num_clusters_needing_refinement"] == 0, "Expected 0 clusters needing refinement"

if __name__ == "__main__":
    run_tests()