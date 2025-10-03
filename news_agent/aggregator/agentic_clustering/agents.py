import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from news_agent.aggregator.models import ContentChunk, ContentCluster, ClusterMetadata
from news_agent.aggregator.embeddings import EmbeddingManager
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class AgenticClusteringConfig(BaseModel):
    """Configuration for the agentic clustering process."""
    max_iterations: int = Field(10, description="Maximum number of refinement iterations.")
    initial_grouping_threshold: float = Field(0.7, description="Similarity threshold for initial grouping.")
    proposer_agent_prompt: str = Field(..., description="Prompt for the Proposer Agent.")
    evaluator_agent_prompt: str = Field(..., description="Prompt for the Evaluator Agent.")
    refiner_agent_prompt: str = Field(..., description="Prompt for the Refiner Agent.")
    min_cluster_size: int = Field(2, description="Minimum number of chunks for a valid cluster.")
    max_cluster_size: int = Field(50, description="Maximum number of chunks for a cluster before considering splitting.")
    similarity_metric: str = Field("cosine", description="Similarity metric for embedding comparisons.")

class BaseAgent:
    """Base class for all clustering agents."""
    def __init__(self, config: AgenticClusteringConfig, embedding_manager: EmbeddingManager, llm: Any):
        self.config = config
        self.embedding_manager = embedding_manager
        self.llm = llm
        self.proposer_prompt = ChatPromptTemplate.from_template(config.proposer_agent_prompt)
        self.evaluator_prompt = ChatPromptTemplate.from_template(config.evaluator_agent_prompt)
        self.refiner_prompt = ChatPromptTemplate.from_template(config.refiner_agent_prompt)

    def _compute_centroid(self, chunks: List[ContentChunk]) -> Optional[List[float]]:
        """Compute the centroid of a list of content chunks."""
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
        if not embeddings:
            return None
        return self.embedding_manager.compute_centroid(embeddings)

    def _calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate similarity between two embeddings."""
        return self.embedding_manager.calculate_similarity(emb1, emb2)

    def _create_cluster_metadata(self, chunks: List[ContentChunk]) -> ClusterMetadata:
        """
        Create metadata for a cluster based on its chunks.
        (Copied from existing clustering.py, can be refactored later)
        """
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

        primary_ticker = None
        if tickers:
            ticker_counts = {ticker: sum(1 for chunk in chunks if chunk.metadata.ticker == ticker)
                           for ticker in tickers}
            primary_ticker = max(ticker_counts.items(), key=lambda x: x[1])[0]

        time_range = None
        if timestamps:
            time_range = (min(timestamps), max(timestamps))

        # Placeholder for confidence score, actual calculation might involve LLM
        confidence_score = 0.0 # self._calculate_cluster_coherence(chunks)

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
        (Copied from existing clustering.py, can be refactored later)
        """
        if len(chunks) < 2:
            return 1.0

        try:
            embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]
            if len(embeddings) < 2:
                return 0.5

            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = self.embedding_manager.calculate_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)

            return sum(similarities) / len(similarities) if similarities else 0.5

        except Exception as e:
            logger.warning(f"Failed to calculate cluster coherence: {e}")
            return 0.5
from datetime import datetime, timedelta

class ProposerAgent(BaseAgent):
    """Agent responsible for proposing initial clusters or assigning unassigned chunks."""
    def propose_clusters(self, chunks: List[ContentChunk]) -> Tuple[List[ContentCluster], List[ContentChunk]]:
        """
        Propose initial clusters based on semantic similarity.
        This is a simplified initial implementation.
        """
        logger.info(f"ProposerAgent: Proposing clusters for {len(chunks)} chunks.")
        clusters = []
        assigned_chunk_ids = set()

        # Simple greedy clustering for initial proposal
        for i, chunk1 in enumerate(chunks):
            if chunk1.id in assigned_chunk_ids:
                continue

            current_cluster_chunks = [chunk1]
            assigned_chunk_ids.add(chunk1.id)

            for j, chunk2 in enumerate(chunks):
                if i == j or chunk2.id in assigned_chunk_ids:
                    continue

                if chunk1.embedding and chunk2.embedding:
                    similarity = self._calculate_similarity(chunk1.embedding, chunk2.embedding)
                    if similarity >= self.config.initial_grouping_threshold:
                        current_cluster_chunks.append(chunk2)
                        assigned_chunk_ids.add(chunk2.id)

            if len(current_cluster_chunks) >= self.config.min_cluster_size:
                centroid = self._compute_centroid(current_cluster_chunks)
                metadata = self._create_cluster_metadata(current_cluster_chunks)
                cluster = ContentCluster(
                    id=f"cluster_prop_{len(clusters)}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    chunks=current_cluster_chunks,
                    centroid=centroid,
                    metadata=metadata
                )
                clusters.append(cluster)
            else:
                # If current_cluster_chunks did not form a valid cluster,
                # ensure their IDs are removed from assigned_chunk_ids
                # so they can be picked up as unassigned.
                for c in current_cluster_chunks:
                    assigned_chunk_ids.discard(c.id)

        # Any chunks not in assigned_chunk_ids are effectively unassigned
        unassigned_chunks = [chunk for chunk in chunks if chunk.id not in assigned_chunk_ids]
        
        logger.info(f"ProposerAgent: Proposed {len(clusters)} clusters, {len(unassigned_chunks)} chunks unassigned.")
        return clusters, unassigned_chunks

class EvaluatorAgent(BaseAgent):
    """Agent responsible for evaluating the quality of proposed or existing clusters."""
    def evaluate_clusters(self, clusters: List[ContentCluster]) -> Dict[str, Any]:
        """
        Evaluate clusters based on internal coherence, separation, and LLM-based reasoning.
        Returns a dictionary of evaluations for each cluster.
        """
        logger.info(f"EvaluatorAgent: Evaluating {len(clusters)} clusters.")
        evaluations = {}
        for cluster in clusters:
            coherence = self._calculate_cluster_coherence(cluster.chunks)
            
            # Prepare content for LLM evaluation
            cluster_content_summary = self._get_cluster_content_summary(cluster)
            
            # LLM call for semantic evaluation
            llm_chain = self.evaluator_prompt | self.llm
            llm_response = llm_chain.invoke({"cluster_summary": cluster_content_summary}).content
            
            evaluations[cluster.id] = {
                "coherence_score": coherence,
                "llm_evaluation": llm_response,
                "needs_refinement": "refine" in llm_response.lower() or coherence < self.config.initial_grouping_threshold
            }
            logger.debug(f"EvaluatorAgent: Cluster {cluster.id} coherence: {coherence:.2f}, LLM: {llm_response}, Needs Refinement: {evaluations[cluster.id]['needs_refinement']}") # Added Needs Refinement to log
        return evaluations

    def _get_cluster_content_summary(self, cluster: ContentCluster) -> str:
        """Generate a summary of the cluster's content for LLM evaluation."""
        titles = [chunk.metadata.title for chunk in cluster.chunks if chunk.metadata.title]
        summaries = [chunk.content[:200] + "..." if chunk.content else "" for chunk in cluster.chunks] # First 200 chars
        
        summary_str = f"Cluster ID: {cluster.id}\n"
        summary_str += f"Number of chunks: {len(cluster.chunks)}\n"
        summary_str += f"Topics: {', '.join(cluster.metadata.topics)}\n"
        summary_str += f"Primary Ticker: {cluster.metadata.primary_ticker or 'N/A'}\n"
        summary_str += "Titles:\n" + "\n".join([f"- {t}" for t in titles[:5]]) # Limit to 5 titles
        summary_str += "\nSample Content Snippets:\n" + "\n".join([f"- {s}" for s in summaries[:3]]) # Limit to 3 snippets
        
        return summary_str

class RefinerAgent(BaseAgent):
    """Agent responsible for refining clusters based on evaluation feedback."""
    def refine_clusters(self, clusters: List[ContentCluster], 
                        evaluations: Dict[str, Any]) -> Tuple[List[ContentCluster], List[ContentChunk]]:
        """
        Refine clusters by merging, splitting, or reassigning chunks.
        """
        logger.info(f"RefinerAgent: Refining {len(clusters)} clusters based on evaluations.")
        refined_clusters = []
        unassigned_chunks_from_refinement = []

        for cluster in clusters:
            evaluation = evaluations.get(cluster.id, {})
            if evaluation.get("needs_refinement"):
                logger.debug(f"RefinerAgent: Refining cluster {cluster.id} due to evaluation: {evaluation}")
                # Example refinement logic:
                if "too large" in evaluation.get("llm_evaluation", "").lower():
                    # Attempt to split large clusters
                    split_results = self._split_cluster(cluster)
                    refined_clusters.extend(split_results)
                elif "too small" in evaluation.get("llm_evaluation", "").lower():
                    # Disband small clusters, reassign chunks
                    unassigned_chunks_from_refinement.extend(cluster.chunks)
                elif "diverse topics" in evaluation.get("llm_evaluation", "").lower():
                    # Re-evaluate chunks within the cluster for potential reassignment
                    reassigned_chunks, kept_chunks = self._reassign_chunks_within_cluster(cluster)
                    if kept_chunks:
                        refined_clusters.append(ContentCluster(
                            id=cluster.id,
                            chunks=kept_chunks,
                            centroid=self._compute_centroid(kept_chunks),
                            metadata=self._create_cluster_metadata(kept_chunks)
                        ))
                    unassigned_chunks_from_refinement.extend(reassigned_chunks)
                else:
                    refined_clusters.append(cluster) # Keep as is if no specific refinement action
            else:
                refined_clusters.append(cluster)
        
        # Attempt to merge similar clusters after individual refinements
        final_clusters = self._merge_similar_clusters_agentic(refined_clusters)

        logger.info(f"RefinerAgent: Refinement complete. {len(final_clusters)} clusters, {len(unassigned_chunks_from_refinement)} chunks unassigned.")
        return final_clusters, unassigned_chunks_from_refinement

    def _split_cluster(self, cluster: ContentCluster) -> List[ContentCluster]:
        """
        Splits a large cluster into smaller ones.
        This could involve re-running a simpler clustering algorithm on its chunks
        or using LLM to identify sub-topics.
        For now, a basic split.
        """
        logger.debug(f"RefinerAgent: Splitting cluster {cluster.id}")
        # Placeholder: In a real scenario, this might involve a sub-clustering step
        # For simplicity, just return chunks as individual clusters for re-evaluation
        if len(cluster.chunks) > self.config.min_cluster_size:
            # A more sophisticated split would involve re-clustering these chunks
            # For now, we'll just return them as individual chunks to be re-processed
            # or form new clusters.
            return [] # Indicate that chunks are now unassigned
        return [cluster] # If cannot split, keep original

    def _reassign_chunks_within_cluster(self, cluster: ContentCluster) -> Tuple[List[ContentChunk], List[ContentChunk]]:
        """
        Reassigns chunks from a cluster if they don't fit well.
        """
        logger.debug(f"RefinerAgent: Reassigning chunks within cluster {cluster.id}")
        reassigned = []
        kept = []
        if not cluster.centroid:
            return cluster.chunks, [] # All chunks are unassigned if no centroid

        for chunk in cluster.chunks:
            if chunk.embedding:
                similarity = self._calculate_similarity(chunk.embedding, cluster.centroid)
                if similarity < self.config.initial_grouping_threshold: # Use a stricter threshold for reassignment
                    reassigned.append(chunk)
                else:
                    kept.append(chunk)
            else:
                reassigned.append(chunk) # Chunks without embeddings are always reassigned
        return reassigned, kept

    def _merge_similar_clusters_agentic(self, clusters: List[ContentCluster]) -> List[ContentCluster]:
        """
        Agentic approach to merging similar clusters.
        This could involve LLM reasoning to decide merges.
        For now, a similarity-based merge.
        """
        if len(clusters) < 2:
            return clusters

        merged_clusters = []
        processed_indices = set()

        for i, cluster1 in enumerate(clusters):
            if i in processed_indices:
                continue

            current_merged_chunks = list(cluster1.chunks)
            current_merged_ids = {chunk.id for chunk in cluster1.chunks}
            
            potential_merge_partners = [cluster1]

            for j, cluster2 in enumerate(clusters):
                if i == j or j in processed_indices:
                    continue

                if cluster1.centroid and cluster2.centroid:
                    similarity = self._calculate_similarity(cluster1.centroid, cluster2.centroid)
                    if similarity >= self.config.initial_grouping_threshold: # Use initial grouping threshold for merging
                        potential_merge_partners.append(cluster2)
            
            if len(potential_merge_partners) > 1:
                # Perform the merge
                all_chunks_to_merge = []
                for p_cluster in potential_merge_partners:
                    all_chunks_to_merge.extend(p_cluster.chunks)
                    processed_indices.add(clusters.index(p_cluster)) # Mark as processed

                new_centroid = self._compute_centroid(all_chunks_to_merge)
                new_metadata = self._create_cluster_metadata(all_chunks_to_merge)
                
                merged_cluster = ContentCluster(
                    id=f"merged_agentic_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    chunks=all_chunks_to_merge,
                    centroid=new_centroid,
                    metadata=new_metadata
                )
                merged_clusters.append(merged_cluster)
            else:
                merged_clusters.append(cluster1)
                processed_indices.add(i)
        
        return merged_clusters