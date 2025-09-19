"""
Main aggregator class that orchestrates the entire news aggregation pipeline.

This module provides the primary AggregatorAgent class that coordinates
all components of the aggregation system: preprocessing, embedding,
deduplication, clustering, scoring, and summarization.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dotenv import load_dotenv
import time

from .models import ContentChunk, ContentCluster, AggregatorOutput
from .config import AggregatorConfig
from .preprocessor import TextPreprocessor
from .embeddings import EmbeddingManager
from .deduplication import DeduplicationEngine
from .clustering import ClusteringEngine
from .scoring import ClusterScorer
from .summarizer import GeminiSummarizer
from .supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)
load_dotenv()

class AggregatorAgent:
    """
    Main aggregation agent that orchestrates the entire pipeline.
    
    This class coordinates all components to:
    1. Process and clean text content
    2. Generate semantic embeddings
    3. Remove duplicates
    4. Create semantic clusters
    5. Score and rank clusters
    6. Generate AI summaries
    7. Store structured output
    
    Features:
    - Complete pipeline orchestration
    - Real-time processing support
    - Database integration
    - Error handling and recovery
    - Performance monitoring
    - Configurable processing parameters
    """
    
    def __init__(self, config: Optional[AggregatorConfig] = None,
                 gemini_api_key: Optional[str] = None,
                 supabase_url: Optional[str] = None,
                 supabase_key: Optional[str] = None):
        """
        Initialize the aggregator agent.
        
        Args:
            config: Aggregator configuration (uses default if None)
            gemini_api_key: API key for Gemini (can also be in config)
            supabase_url: Supabase project URL (can also be in config)
            supabase_key: Supabase API key (can also be in config)
        """
        self.config = config or AggregatorConfig()
        
        # Override config with provided parameters
        if supabase_url:
            self.config.supabase.url = supabase_url
        if supabase_key:
            self.config.supabase.key = supabase_key
        if gemini_api_key:
            self.config.summarizer.api_key = gemini_api_key
        
        # Validate configuration
        self.config.validate()
        
        # Initialize components
        self._initialize_components()
        
        # Performance tracking
        self.stats = {
            'total_processed': 0,
            'total_clusters_created': 0,
            'processing_times': [],
            'last_processing_time': None
        }
        
        logger.info("AggregatorAgent initialized successfully")
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        try:
            # Text preprocessing
            self.preprocessor = TextPreprocessor(self.config.preprocessing)
            logger.debug("TextPreprocessor initialized")
            
            # Embedding generation
            self.embedding_manager = EmbeddingManager(self.config.embedding)
            logger.debug("EmbeddingManager initialized")
            
            # Deduplication
            self.deduplication_engine = DeduplicationEngine(
                self.config.deduplication, 
                self.embedding_manager
            )
            logger.debug("DeduplicationEngine initialized")
            
            # Clustering
            self.clustering_engine = ClusteringEngine(
                self.config.clustering,
                self.embedding_manager
            )
            logger.debug("ClusteringEngine initialized")
            
            # Scoring
            self.cluster_scorer = ClusterScorer(self.config.scoring)
            logger.debug("ClusterScorer initialized")
            
            # Summarization
            self.summarizer = GeminiSummarizer(
                self.config.summarizer,
                getattr(self.config.summarizer, 'api_key', None)
            )
            logger.debug("GeminiSummarizer initialized")
            
            # Supabase manager (optional)
            if self.config.supabase.url and self.config.supabase.key:
                try:
                    self.supabase_manager = SupabaseManager(
                        self.config.supabase.url,
                        self.config.supabase.key,
                        self.config.supabase.vector_dimension
                    )
                    logger.debug("SupabaseManager initialized")
                    # Keep database_manager reference for backward compatibility
                    self.database_manager = self.supabase_manager
                except Exception as e:
                    logger.warning(f"Failed to initialize Supabase manager: {e}")
                    self.supabase_manager = None
                    self.database_manager = None
            else:
                self.supabase_manager = None
                self.database_manager = None
                logger.warning("No Supabase configuration found - database operations will be skipped")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def process_planner_results(self, planner_results: Dict[str, Any], 
                              user_preferences: Optional[Dict[str, Any]] = None) -> AggregatorOutput:
        """
        Process results from PlannerAgent through the aggregation pipeline.
        
        Args:
            planner_results: Results from PlannerAgent.run_async()
            user_preferences: Optional user preferences for scoring
            
        Returns:
            AggregatorOutput with clustered and summarized content
        """
        start_time = time.time()
        
        try:
            logger.info("Starting aggregation pipeline")
            
            # Stage 1: Preprocessing
            logger.info("Stage 1: Text preprocessing")
            chunks = self.preprocessor.process_planner_results(planner_results)
            logger.info(f"Preprocessed {len(chunks)} content chunks")
            
            if not chunks:
                return self._create_empty_output("No valid content chunks after preprocessing")
            
            # Stage 2: Generate embeddings
            logger.info("Stage 2: Embedding generation")
            chunks_with_embeddings = self.embedding_manager.embed_chunks(chunks)
            logger.info(f"Generated embeddings for {len(chunks_with_embeddings)} chunks")
            
            # Stage 3: Deduplication
            logger.info("Stage 3: Content deduplication")
            deduped_chunks = self.deduplication_engine.deduplicate_chunks(chunks_with_embeddings)
            dedup_stats = self.deduplication_engine.get_deduplication_stats(
                chunks_with_embeddings, deduped_chunks
            )
            logger.info(f"Deduplication: {len(chunks_with_embeddings)} -> {len(deduped_chunks)} chunks "
                       f"({dedup_stats['removal_percentage']:.1f}% removed)")
            
            if not deduped_chunks:
                return self._create_empty_output("No chunks remaining after deduplication")
            
            # Stage 4: Clustering
            logger.info("Stage 4: Semantic clustering")
            clusters = self.clustering_engine.cluster_chunks(deduped_chunks)
            cluster_stats = self.clustering_engine.get_cluster_summary_stats(clusters)
            logger.info(f"Created {len(clusters)} clusters from {len(deduped_chunks)} chunks")
            
            if not clusters:
                return self._create_empty_output("No clusters created from content")
            
            # Stage 5: Cluster scoring and ranking
            logger.info("Stage 5: Cluster scoring")
            scored_clusters = self.cluster_scorer.score_clusters(clusters, user_preferences)
            
            # Limit to top clusters
            max_clusters = self.config.processing.max_clusters_output
            top_clusters = scored_clusters[:max_clusters]
            logger.info(f"Selected top {len(top_clusters)} clusters for output")
            
            # Stage 6: Summary generation
            logger.info("Stage 6: Summary generation")
            summaries = self.summarizer.summarize_clusters_batch(top_clusters)
            
            # Attach summaries to clusters
            for cluster, summary in zip(top_clusters, summaries):
                cluster.summary = summary
            
            logger.info(f"Generated {len(summaries)} summaries")
            
            # Stage 7: Database storage (if available)
            if self.database_manager:
                logger.info("Stage 7: Database storage")
                self._store_results_in_database(top_clusters, deduped_chunks)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.stats['processing_times'].append(processing_time)
            self.stats['last_processing_time'] = processing_time
            self.stats['total_processed'] += len(chunks)
            self.stats['total_clusters_created'] += len(top_clusters)
            
            # Create output
            output = self._create_aggregator_output(
                top_clusters, 
                processing_time,
                dedup_stats,
                cluster_stats
            )
            
            logger.info(f"Aggregation pipeline completed in {processing_time:.2f}s")
            return output
            
        except Exception as e:
            logger.error(f"Aggregation pipeline failed: {e}")
            processing_time = time.time() - start_time
            return self._create_error_output(str(e), processing_time)
    
    async def process_planner_results_async(self, planner_results: List[Dict[str, Any]],
                                          user_preferences: Optional[Dict[str, Any]] = None) -> List[AggregatorOutput]:
        """
        Asynchronously process planner results.
        
        Args:
            planner_results: Results from PlannerAgent
            user_preferences: Optional user preferences
            
        Returns:
            AggregatorOutput with clustered and summarized content
        """
        start_time = time.time()
        
        outputs = []
        for planner_result in planner_results:
            try:
                logger.info("Starting async aggregation pipeline for a single planner result")
                
                # Stage 1: Preprocessing (sync)
                chunks = self.preprocessor.process_planner_results(planner_result)
                logger.info(f"Preprocessed {len(chunks)} content chunks")
                
                if not chunks:
                    outputs.append(self._create_empty_output("No valid content chunks after preprocessing"))
                    continue
                
                # Stage 2: Generate embeddings (async)
                chunks_with_embeddings = await self.embedding_manager.embed_chunks_async(chunks)
                logger.info(f"Generated embeddings for {len(chunks_with_embeddings)} chunks")
                
                # Stage 3: Deduplication (sync)
                deduped_chunks = self.deduplication_engine.deduplicate_chunks(chunks_with_embeddings)
                dedup_stats = self.deduplication_engine.get_deduplication_stats(
                    chunks_with_embeddings, deduped_chunks
                )
                logger.info(f"Deduplicated to {len(deduped_chunks)} chunks")
                
                if not deduped_chunks:
                    outputs.append(self._create_empty_output("No chunks remaining after deduplication"))
                    continue
                
                # Stage 4: Clustering (sync)
                clusters = self.clustering_engine.cluster_chunks(deduped_chunks)
                cluster_stats = self.clustering_engine.get_cluster_summary_stats(clusters)
                logger.info(f"Created {len(clusters)} clusters")
                
                if not clusters:
                    outputs.append(self._create_empty_output("No clusters created from content"))
                    continue
                
                # Stage 5: Scoring (sync)
                scored_clusters = self.cluster_scorer.score_clusters(clusters, user_preferences)
                top_clusters = scored_clusters[:self.config.processing.max_clusters_output]
                
                # Stage 6: Summary generation (async)
                summaries = await self.summarizer.summarize_clusters_async(top_clusters)
                
                # Attach summaries
                for cluster, summary in zip(top_clusters, summaries):
                    cluster.summary = summary
                
                # Stage 7: Database storage (if available)
                if self.database_manager:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._store_results_in_database,
                        top_clusters,
                        deduped_chunks
                    )
                
                processing_time = time.time() - start_time # This should be per-result processing time
                self.stats['processing_times'].append(processing_time)
                self.stats['last_processing_time'] = processing_time
                
                outputs.append(self._create_aggregator_output(
                    top_clusters,
                    processing_time,
                    dedup_stats,
                    cluster_stats
                ))
                
                logger.info(f"Async aggregation pipeline for a single result completed in {processing_time:.2f}s")
            
            except Exception as e:
                logger.error(f"Async aggregation pipeline failed for a result: {e}")
                processing_time = time.time() - start_time # This should be per-result processing time
                outputs.append(self._create_error_output(str(e), processing_time))
                
        return outputs
    
    def process_new_chunks(self, new_chunks: List[ContentChunk],
                          existing_clusters: Optional[List[ContentCluster]] = None,
                          user_preferences: Optional[Dict[str, Any]] = None) -> AggregatorOutput:
        """
        Process new content chunks, updating existing clusters if provided.
        
        Args:
            new_chunks: New content chunks to process
            existing_clusters: Existing clusters to update (optional)
            user_preferences: User preferences for scoring
            
        Returns:
            Updated aggregation output
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing {len(new_chunks)} new chunks")
            
            # Generate embeddings for new chunks
            embedded_chunks = self.embedding_manager.embed_chunks(new_chunks)
            
            # Check for duplicates against existing content if available
            if self.database_manager:
                # Get recent chunks from database for duplicate checking
                recent_db_chunks = self._get_recent_chunks_from_db()
                unique_chunks, duplicate_chunks = self.deduplication_engine.find_duplicates_in_new_chunks(
                    embedded_chunks, recent_db_chunks
                )
                logger.info(f"Found {len(duplicate_chunks)} duplicates, {len(unique_chunks)} unique")
            else:
                # Just dedupe among new chunks
                unique_chunks = self.deduplication_engine.deduplicate_chunks(embedded_chunks)
            
            if not unique_chunks:
                return self._create_empty_output("No unique chunks to process")
            
            # Update existing clusters or create new ones
            if existing_clusters:
                updated_clusters, unassigned_chunks = self.clustering_engine.update_clusters_with_new_chunks(
                    unique_chunks, existing_clusters
                )
                
                # Create new clusters from unassigned chunks
                new_clusters = self.clustering_engine.create_clusters_from_unassigned(unassigned_chunks)
                
                all_clusters = updated_clusters + new_clusters
            else:
                # Create clusters from scratch
                all_clusters = self.clustering_engine.cluster_chunks(unique_chunks)
            
            # Score and rank clusters
            scored_clusters = self.cluster_scorer.score_clusters(all_clusters, user_preferences)
            top_clusters = scored_clusters[:self.config.processing.max_clusters_output]
            
            # Generate summaries for new/updated clusters
            clusters_needing_summaries = [c for c in top_clusters if not c.summary]
            if clusters_needing_summaries:
                new_summaries = self.summarizer.summarize_clusters_batch(clusters_needing_summaries)
                for cluster, summary in zip(clusters_needing_summaries, new_summaries):
                    cluster.summary = summary
            
            # Store updates in database
            if self.database_manager:
                self._store_results_in_database(top_clusters, unique_chunks)
            
            processing_time = time.time() - start_time
            output = self._create_aggregator_output(top_clusters, processing_time)
            
            logger.info(f"New chunk processing completed in {processing_time:.2f}s")
            return output
            
        except Exception as e:
            logger.error(f"New chunk processing failed: {e}")
            processing_time = time.time() - start_time
            return self._create_error_output(str(e), processing_time)
    
    def _store_results_in_database(self, clusters: List[ContentCluster], chunks: List[ContentChunk]):
        """Store results in database."""
        try:
            # Store chunks
            chunk_ids = self.database_manager.insert_chunks_batch(chunks)
            logger.debug(f"Stored {len(chunk_ids)} chunks in database")
            
            # Store clusters
            for cluster in clusters:
                cluster_id = self.database_manager.insert_cluster(cluster)
                
                # Update chunk cluster assignments
                chunk_ids_for_cluster = [chunk.id for chunk in cluster.chunks]
                self.database_manager.update_chunk_cluster_assignment(chunk_ids_for_cluster, cluster_id)
                
                # Store summary
                if cluster.summary:
                    self.database_manager.insert_cluster_summary(cluster.summary)
            
            logger.info("Results stored in database successfully")
            
        except Exception as e:
            logger.error(f"Failed to store results in database: {e}")
    
    def _get_recent_chunks_from_db(self, hours: int = 24) -> List[ContentChunk]:
        """Get recent chunks from database for duplicate checking."""
        try:
            if not self.database_manager:
                return []
            
            # Use the new Supabase method
            recent_data = self.database_manager.get_recent_chunks_from_db(hours)
            
            # Convert to ContentChunk objects if needed
            # For now, return the raw data since deduplication engine can handle it
            return recent_data
            
        except Exception as e:
            logger.warning(f"Failed to get recent chunks from database: {e}")
            return []
    
    def _create_aggregator_output(self, clusters: List[ContentCluster],
                                 processing_time: float,
                                 dedup_stats: Optional[Dict[str, Any]] = None,
                                 cluster_stats: Optional[Dict[str, Any]] = None) -> AggregatorOutput:
        """Create structured aggregator output."""
        
        processing_stats = {
            'processing_time_seconds': processing_time,
            'total_clusters': len(clusters),
            'total_sources': sum(cluster.source_count for cluster in clusters),
            'total_chunks_processed': sum(cluster.chunk_count for cluster in clusters),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if dedup_stats:
            processing_stats['deduplication'] = dedup_stats
        
        if cluster_stats:
            processing_stats['clustering'] = cluster_stats
        
        return AggregatorOutput(
            clusters=clusters,
            processing_stats=processing_stats
        )
    
    def _create_empty_output(self, reason: str) -> AggregatorOutput:
        """Create empty output with reason."""
        return AggregatorOutput(
            clusters=[],
            processing_stats={
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_clusters': 0,
                'total_sources': 0
            }
        )
    
    def _create_error_output(self, error_message: str, processing_time: float) -> AggregatorOutput:
        """Create error output."""
        return AggregatorOutput(
            clusters=[],
            processing_stats={
                'error': error_message,
                'processing_time_seconds': processing_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_clusters': 0,
                'total_sources': 0
            }
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the aggregator."""
        processing_times = self.stats['processing_times']
        
        stats = {
            'total_runs': len(processing_times),
            'total_chunks_processed': self.stats['total_processed'],
            'total_clusters_created': self.stats['total_clusters_created'],
            'last_processing_time': self.stats['last_processing_time']
        }
        
        if processing_times:
            stats.update({
                'avg_processing_time': sum(processing_times) / len(processing_times),
                'min_processing_time': min(processing_times),
                'max_processing_time': max(processing_times)
            })
        
        return stats
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'supabase_manager') and self.supabase_manager:
                self.supabase_manager.close()
            
            if hasattr(self, 'database_manager') and self.database_manager:
                self.database_manager.close()
            
            if hasattr(self, 'embedding_manager'):
                # Embedding manager cleanup is handled in its destructor
                pass
            
            logger.info("AggregatorAgent cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    
    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()


# Convenience function for quick usage
def create_aggregator_agent(gemini_api_key: str,
                           supabase_url: Optional[str] = None,
                           supabase_key: Optional[str] = None,
                           config_overrides: Optional[Dict[str, Any]] = None) -> AggregatorAgent:
    """
    Create a configured aggregator agent with common settings.
    
    Args:
        gemini_api_key: Gemini API key for summarization
        supabase_url: Optional Supabase project URL
        supabase_key: Optional Supabase API key
        config_overrides: Optional configuration overrides
        
    Returns:
        Configured AggregatorAgent instance
    """
    config = AggregatorConfig()
    
    # Apply overrides if provided
    if config_overrides:
        for section_name, section_overrides in config_overrides.items():
            if hasattr(config, section_name):
                section_obj = getattr(config, section_name)
                for key, value in section_overrides.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
    
    return AggregatorAgent(
        config=config,
        gemini_api_key=gemini_api_key,
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )


# Example usage function
async def example_usage():
    """Example of how to use the AggregatorAgent."""
    
    # Mock PlannerAgent results for demonstration
    mock_planner_results = {
        "breaking_news": [
            {
                "title": "Breaking: Major Tech Company Announces New AI Initiative",
                "url": "https://example.com/news/1",
                "description": "A major technology company today announced a groundbreaking AI initiative...",
                "source_retriever": "TavilyRetriever"
            }
        ],
        "financial_news": [
            {
                "title": "Q3 Earnings Beat Expectations for Tech Giant",
                "url": "https://example.com/finance/1", 
                "description": "The company reported strong Q3 earnings that exceeded analyst expectations...",
                "source_retriever": "SerperRetriever"
            }
        ],
        "general_news": [],
        "sec_filings": []
    }
    
    # Create aggregator (would need real API key)
    try:
        import os
        aggregator = create_aggregator_agent(
            gemini_api_key=os.getenv("GEMINI_API_KEY", "your-gemini-key"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY")
        )
        
        # Process results
        output = await aggregator.process_planner_results_async(mock_planner_results)
        
        # Print summary
        logger.info(f"Generated {len(output.clusters)} clusters")
        for i, cluster in enumerate(output.clusters):
            logger.info(f"\nCluster {i+1}:")
            logger.info(f"  Sources: {cluster.source_count}")
            logger.info(f"  Summary: {cluster.summary.summary[:100]}..." if cluster.summary else "  No summary")
        
        # Cleanup
        aggregator.cleanup()
        
    except Exception as e:
        logger.error(f"Example failed: {e}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
