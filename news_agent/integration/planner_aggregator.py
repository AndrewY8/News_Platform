"""
Enhanced PlannerAgent with integrated aggregation capabilities.

This module extends the existing PlannerAgent to include automatic
aggregation and summarization of retrieved content using the
news aggregator system.
"""

import logging
import asyncio
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import existing PlannerAgent
from ..agent import PlannerAgent

# Import aggregator components
from ..aggregator import AggregatorAgent, AggregatorConfig, create_aggregator_agent
from ..aggregator.models import AggregatorOutput

logger = logging.getLogger(__name__)


class EnhancedPlannerAgent:
    """
    Enhanced PlannerAgent that combines content retrieval with aggregation.
    
    This class wraps the existing PlannerAgent and adds automatic
    aggregation capabilities, providing:
    - Semantic clustering of retrieved content
    - Duplicate removal across sources
    - AI-powered summarization
    - Structured output for frontend consumption
    """
    
    def __init__(self, 
                 max_concurrent_retrievers: int = 5,
                 gemini_api_key: Optional[str] = None,
                 database_url: Optional[str] = None,
                 aggregator_config: Optional[AggregatorConfig] = None,
                 enable_aggregation: bool = True):
        """
        Initialize the enhanced planner agent.
        
        Args:
            max_concurrent_retrievers: Max concurrent retrievers for PlannerAgent
            gemini_api_key: API key for Gemini summarization
            database_url: Database connection string
            aggregator_config: Custom aggregator configuration
            enable_aggregation: Whether to enable aggregation (can be disabled for testing)
        """
        # Initialize base PlannerAgent
        self.planner_agent = PlannerAgent(max_concurrent_retrievers)
        
        # Initialize aggregator if enabled
        self.enable_aggregation = enable_aggregation
        self.aggregator = None
        
        if enable_aggregation:
            try:
                if aggregator_config:
                    # Read Supabase credentials from environment if not in config
                    supabase_url = aggregator_config.supabase.url or os.getenv("SUPABASE_URL")
                    supabase_key = aggregator_config.supabase.key or os.getenv("SUPABASE_KEY")
                    
                    self.aggregator = AggregatorAgent(
                        config=aggregator_config,
                        gemini_api_key=gemini_api_key,
                        supabase_url=supabase_url,
                        supabase_key=supabase_key
                    )
                else:
                    # Read Supabase credentials from environment
                    supabase_url = os.getenv("SUPABASE_URL")
                    supabase_key = os.getenv("SUPABASE_KEY")
                    
                    self.aggregator = create_aggregator_agent(
                        gemini_api_key=gemini_api_key or "dummy-key",  # Will need real key
                        supabase_url=supabase_url,
                        supabase_key=supabase_key
                    )
                
                logger.info("Aggregation enabled for EnhancedPlannerAgent")
                
            except Exception as e:
                logger.warning(f"Failed to initialize aggregator: {e}")
                logger.warning("Falling back to PlannerAgent-only mode")
                self.enable_aggregation = False
        
        logger.info(f"EnhancedPlannerAgent initialized (aggregation: {self.enable_aggregation})")
    
    async def run_async(self, query: str, 
                       user_preferences: Optional[Dict[str, Any]] = None,
                       return_aggregated: bool = True) -> Dict[str, Any]:
        """
        Enhanced async run method with optional aggregation.
        
        Args:
            query: Search query
            user_preferences: User preferences for relevance scoring
            return_aggregated: Whether to return aggregated results
            
        Returns:
            Dictionary containing both raw and aggregated results
        """
        try:
            logger.info(f"Starting enhanced search for query: '{query}'")
            
            # Step 1: Run original PlannerAgent
            start_time = datetime.utcnow()
            planner_results = await self.planner_agent.run_async(query)
            retrieval_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"PlannerAgent completed in {retrieval_time:.2f}s")
            
            # Step 2: Aggregate results if enabled and requested
            aggregated_results = None
            if self.enable_aggregation and return_aggregated and self.aggregator:
                try:
                    logger.info("Starting aggregation process")
                    aggregation_start = datetime.utcnow()
                    
                    aggregated_results = await self.aggregator.process_planner_results_async(
                        planner_results, user_preferences
                    )
                    
                    aggregation_time = (datetime.utcnow() - aggregation_start).total_seconds()
                    logger.info(f"Aggregation completed in {aggregation_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"Aggregation failed: {e}")
                    # Continue with just planner results
                    aggregated_results = None
            
            # Step 3: Combine results
            enhanced_results = self._combine_results(
                planner_results, 
                aggregated_results,
                retrieval_time,
                query,
                user_preferences
            )
            
            total_time = (datetime.utcnow() - start_time).total_seconds()
            enhanced_results['processing_stats']['total_time'] = total_time
            
            logger.info(f"Enhanced search completed in {total_time:.2f}s")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Enhanced PlannerAgent failed: {e}")
            # Fallback to original planner results
            try:
                return await self.planner_agent.run_async(query)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return self._create_error_response(str(e))
    
    def run(self, query: str, 
            user_preferences: Optional[Dict[str, Any]] = None,
            return_aggregated: bool = True) -> Dict[str, Any]:
        """
        Synchronous wrapper for enhanced run method.
        
        Args:
            query: Search query
            user_preferences: User preferences for relevance scoring
            return_aggregated: Whether to return aggregated results
            
        Returns:
            Dictionary containing both raw and aggregated results
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.run_async(query, user_preferences, return_aggregated)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.run_async(query, user_preferences, return_aggregated)
                )
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(self.run_async(query, user_preferences, return_aggregated))
    
    def _combine_results(self, planner_results: Dict[str, Any], 
                        aggregated_results: Optional[AggregatorOutput],
                        retrieval_time: float,
                        query: str,
                        user_preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine raw planner results with aggregated results.
        
        Args:
            planner_results: Raw results from PlannerAgent
            aggregated_results: Aggregated results from AggregatorAgent
            retrieval_time: Time spent on retrieval
            query: Original query
            user_preferences: User preferences used
            
        Returns:
            Combined results dictionary
        """
        # Start with original planner results
        enhanced_results = planner_results.copy()
        
        # Add aggregation section
        if aggregated_results:
            enhanced_results['aggregation'] = {
                'enabled': True,
                'clusters': [cluster.to_dict() for cluster in aggregated_results.clusters],
                'stats': aggregated_results.processing_stats,
                'cluster_count': len(aggregated_results.clusters),
                'total_sources': aggregated_results.total_sources
            }
            
            # Add structured summaries for easy frontend consumption
            enhanced_results['summaries'] = []
            for cluster in aggregated_results.clusters:
                if cluster.summary:
                    structured_summary = {
                        'id': cluster.id,
                        'title': self._generate_cluster_title(cluster),
                        'summary': cluster.summary.summary,
                        'key_points': cluster.summary.key_points,
                        'sources': [source.to_dict() for source in cluster.get_sources()],
                        'metadata': {
                            'ticker': cluster.metadata.primary_ticker,
                            'topics': cluster.metadata.topics,
                            'source_count': cluster.source_count,
                            'confidence': cluster.summary.confidence,
                            'cluster_score': getattr(cluster.metadata, 'final_score', None)
                        }
                    }
                    enhanced_results['summaries'].append(structured_summary)
        else:
            enhanced_results['aggregation'] = {
                'enabled': self.enable_aggregation,
                'clusters': [],
                'stats': {'error': 'Aggregation failed or disabled'},
                'cluster_count': 0,
                'total_sources': 0
            }
            enhanced_results['summaries'] = []
        
        # Enhanced processing stats
        if 'processing_stats' not in enhanced_results:
            enhanced_results['processing_stats'] = {}
        
        enhanced_results['processing_stats'].update({
            'query': query,
            'retrieval_time': retrieval_time,
            'aggregation_enabled': self.enable_aggregation,
            'user_preferences_used': user_preferences is not None,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return enhanced_results
    
    def _generate_cluster_title(self, cluster) -> str:
        """Generate a readable title for a cluster."""
        if cluster.metadata.primary_ticker:
            if cluster.metadata.topics:
                main_topic = cluster.metadata.topics[0].replace('_', ' ').title()
                return f"{cluster.metadata.primary_ticker}: {main_topic}"
            else:
                return f"{cluster.metadata.primary_ticker} News Update"
        elif cluster.metadata.topics:
            main_topic = cluster.metadata.topics[0].replace('_', ' ').title()
            return f"{main_topic} Update"
        else:
            return f"News Cluster ({cluster.source_count} sources)"
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response in expected format."""
        return {
            "breaking_news": [],
            "financial_news": [],
            "sec_filings": [],
            "general_news": [],
            "errors": [{"retriever": "enhanced_planner_agent", "error": error_message}],
            "retriever_summary": {
                "total_retrievers": 0,
                "successful_retrievers": 0,
                "failed_retrievers": 1,
                "total_articles": 0
            },
            "aggregation": {
                "enabled": False,
                "clusters": [],
                "stats": {"error": error_message},
                "cluster_count": 0,
                "total_sources": 0
            },
            "summaries": [],
            "processing_stats": {
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    def get_aggregator_stats(self) -> Dict[str, Any]:
        """Get performance statistics from the aggregator."""
        if self.aggregator:
            return self.aggregator.get_performance_stats()
        return {"error": "Aggregator not initialized"}
    
    def get_planner_summary(self) -> Dict[str, Any]:
        """Get summary information about the enhanced planner."""
        return {
            "aggregation_enabled": self.enable_aggregation,
            "has_aggregator": self.aggregator is not None,
            "max_concurrent_retrievers": self.planner_agent.max_concurrent_retrievers,
            "aggregator_stats": self.get_aggregator_stats() if self.aggregator else None
        }
    
    def update_user_preferences(self, user_preferences: Dict[str, Any]):
        """
        Update user preferences that will be used for future queries.
        
        Args:
            user_preferences: Dictionary of user preferences
        """
        # Store preferences for use in future queries
        self.default_user_preferences = user_preferences
        logger.info("Updated default user preferences")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.aggregator:
                self.aggregator.cleanup()
            logger.info("EnhancedPlannerAgent cleanup completed")
        except Exception as e:
            logger.error(f"Error during EnhancedPlannerAgent cleanup: {e}")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()


# Convenience functions for easy integration
def create_enhanced_planner(gemini_api_key: str,
                           database_url: Optional[str] = None,
                           supabase_url: Optional[str] = None,
                           supabase_key: Optional[str] = None,
                           max_retrievers: int = 5,
                           config_overrides: Optional[Dict[str, Any]] = None) -> EnhancedPlannerAgent:
    """
    Create an enhanced planner agent with aggregation capabilities.
    
    Args:
        gemini_api_key: Gemini API key for summarization
        database_url: Optional database connection string (legacy parameter)
        supabase_url: Optional Supabase URL (reads from SUPABASE_URL env if None)
        supabase_key: Optional Supabase key (reads from SUPABASE_KEY env if None)
        max_retrievers: Maximum concurrent retrievers
        config_overrides: Optional configuration overrides
        
    Returns:
        Configured EnhancedPlannerAgent
    """
    # Read Supabase credentials from environment if not provided
    if supabase_url is None:
        supabase_url = os.getenv("SUPABASE_URL")
    if supabase_key is None:
        supabase_key = os.getenv("SUPABASE_KEY")
    
    aggregator_config = None
    
    if config_overrides:
        aggregator_config = AggregatorConfig()
        for section_name, section_overrides in config_overrides.items():
            if hasattr(aggregator_config, section_name):
                section_obj = getattr(aggregator_config, section_name)
                for key, value in section_overrides.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
    
    # If we still don't have a config but have Supabase credentials, create one
    if aggregator_config is None and (supabase_url and supabase_key):
        aggregator_config = AggregatorConfig()
        aggregator_config.supabase.url = supabase_url
        aggregator_config.supabase.key = supabase_key
    elif aggregator_config is not None:
        # Update existing config with Supabase credentials
        if supabase_url:
            aggregator_config.supabase.url = supabase_url
        if supabase_key:
            aggregator_config.supabase.key = supabase_key
    
    return EnhancedPlannerAgent(
        max_concurrent_retrievers=max_retrievers,
        gemini_api_key=gemini_api_key,
        database_url=database_url,
        aggregator_config=aggregator_config,
        enable_aggregation=True
    )


def create_basic_planner(max_retrievers: int = 5) -> EnhancedPlannerAgent:
    """
    Create a basic enhanced planner without aggregation (for testing/fallback).
    
    Args:
        max_retrievers: Maximum concurrent retrievers
        
    Returns:
        EnhancedPlannerAgent with aggregation disabled
    """
    return EnhancedPlannerAgent(
        max_concurrent_retrievers=max_retrievers,
        enable_aggregation=False
    )


# Example usage
async def example_enhanced_usage():
    """Example of using the EnhancedPlannerAgent."""
    
    # Create enhanced planner
    planner = create_enhanced_planner(
        gemini_api_key="your-api-key-here",
        database_url="postgresql://user:pass@localhost/db"
    )
    
    # Define user preferences
    user_prefs = {
        'watchlist': ['AAPL', 'GOOGL', 'MSFT'],
        'topics': ['technology', 'artificial_intelligence'],
        'keywords': ['earnings', 'AI', 'innovation']
    }
    
    # Run enhanced search
    try:
        results = await planner.run_async(
            query="AI technology earnings news",
            user_preferences=user_prefs
        )
        
        # Print results
        print(f"Found {len(results['summaries'])} cluster summaries")
        for i, summary in enumerate(results['summaries']):
            print(f"\nSummary {i+1}: {summary['title']}")
            print(f"Sources: {summary['metadata']['source_count']}")
            print(f"Summary: {summary['summary'][:100]}...")
        
        # Cleanup
        planner.cleanup()
        
    except Exception as e:
        print(f"Enhanced planner example failed: {e}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_enhanced_usage())
