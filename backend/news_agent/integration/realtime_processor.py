"""
Real-time processing capabilities for the News Aggregator.

This module provides real-time and near-real-time processing of news content,
including queue management, batch processing, and incremental cluster updates.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from collections import deque, defaultdict
import time
import threading
from dataclasses import dataclass
from queue import Queue, Empty

from ..aggregator.models import ContentChunk, ContentCluster, AggregatorOutput
from ..aggregator.aggregator import AggregatorAgent
from ..aggregator.config import AggregatorConfig

logger = logging.getLogger(__name__)


@dataclass
class ProcessingJob:
    """Represents a processing job in the queue."""
    job_id: str
    content: Dict[str, Any]  # PlannerAgent results or individual chunks
    priority: int = 1  # Higher numbers = higher priority
    created_at: datetime = None
    user_preferences: Optional[Dict[str, Any]] = None
    callback: Optional[Callable] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class RealtimeProcessor:
    """
    Real-time processor for news content aggregation.
    
    Features:
    - Asynchronous job queue management
    - Batch processing with configurable intervals
    - Incremental cluster updates
    - Priority-based processing
    - Background worker threads
    - Callback support for results
    - Performance monitoring
    """
    
    def __init__(self, 
                 aggregator: AggregatorAgent,
                 batch_size: int = 50,
                 batch_interval: int = 30,
                 max_queue_size: int = 1000,
                 num_workers: int = 2,
                 enable_monitoring: bool = True):
        """
        Initialize the real-time processor.
        
        Args:
            aggregator: AggregatorAgent instance
            batch_size: Maximum items per batch
            batch_interval: Batch processing interval in seconds
            max_queue_size: Maximum queue size
            num_workers: Number of background worker threads
            enable_monitoring: Whether to enable performance monitoring
        """
        self.aggregator = aggregator
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        self.enable_monitoring = enable_monitoring
        
        # Queue and processing state
        self.job_queue = Queue(maxsize=max_queue_size)
        self.priority_queue = Queue(maxsize=max_queue_size // 2)  # For high priority jobs
        self.processing = False
        self.workers = []
        self.worker_threads = []
        
        # State management
        self.active_clusters = {}  # cluster_id -> ContentCluster
        self.recent_chunks = deque(maxlen=1000)  # For duplicate checking
        self.last_batch_time = time.time()
        
        # Monitoring and stats
        self.stats = {
            'jobs_processed': 0,
            'jobs_failed': 0,
            'batches_processed': 0,
            'average_batch_size': 0,
            'average_processing_time': 0,
            'queue_size': 0,
            'processing_times': deque(maxlen=100)
        }
        
        # Callbacks for different events
        self.callbacks = {
            'job_completed': [],
            'batch_completed': [],
            'cluster_updated': [],
            'error': []
        }
        
        logger.info(f"RealtimeProcessor initialized with {num_workers} workers")
    
    def start(self):
        """Start the real-time processor."""
        if self.processing:
            logger.warning("Processor is already running")
            return
        
        self.processing = True
        
        # Start worker threads
        for i in range(self.num_workers):
            worker_thread = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=True,
                name=f"RealtimeProcessor-Worker-{i}"
            )
            worker_thread.start()
            self.worker_threads.append(worker_thread)
        
        # Start batch processor thread
        batch_thread = threading.Thread(
            target=self._batch_processor_loop,
            daemon=True,
            name="RealtimeProcessor-BatchProcessor"
        )
        batch_thread.start()
        self.worker_threads.append(batch_thread)
        
        logger.info(f"RealtimeProcessor started with {len(self.worker_threads)} threads")
    
    def stop(self):
        """Stop the real-time processor."""
        if not self.processing:
            return
        
        logger.info("Stopping RealtimeProcessor...")
        self.processing = False
        
        # Wait for threads to finish (with timeout)
        for thread in self.worker_threads:
            thread.join(timeout=5.0)
        
        self.worker_threads.clear()
        logger.info("RealtimeProcessor stopped")
    
    def submit_job(self, 
                   content: Dict[str, Any],
                   priority: int = 1,
                   user_preferences: Optional[Dict[str, Any]] = None,
                   callback: Optional[Callable] = None) -> str:
        """
        Submit a new processing job.
        
        Args:
            content: Content to process (PlannerAgent results format)
            priority: Job priority (higher = more important)
            user_preferences: User preferences for scoring
            callback: Optional callback function for results
            
        Returns:
            Job ID
        """
        job_id = f"job_{int(time.time() * 1000)}_{id(content)}"
        
        job = ProcessingJob(
            job_id=job_id,
            content=content,
            priority=priority,
            user_preferences=user_preferences,
            callback=callback
        )
        
        try:
            if priority > 5:  # High priority jobs
                self.priority_queue.put_nowait(job)
            else:
                self.job_queue.put_nowait(job)
            
            logger.debug(f"Submitted job {job_id} with priority {priority}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            raise
    
    def submit_planner_results(self,
                              planner_results: Dict[str, Any],
                              priority: int = 1,
                              user_preferences: Optional[Dict[str, Any]] = None,
                              callback: Optional[Callable] = None) -> str:
        """
        Submit PlannerAgent results for processing.
        
        Args:
            planner_results: Results from PlannerAgent
            priority: Job priority
            user_preferences: User preferences
            callback: Result callback
            
        Returns:
            Job ID
        """
        return self.submit_job(
            content=planner_results,
            priority=priority,
            user_preferences=user_preferences,
            callback=callback
        )
    
    def _worker_loop(self, worker_id: int):
        """Main worker loop for processing jobs."""
        logger.debug(f"Worker {worker_id} started")
        
        while self.processing:
            try:
                # Try to get high priority job first
                job = None
                try:
                    job = self.priority_queue.get_nowait()
                except Empty:
                    try:
                        job = self.job_queue.get(timeout=1.0)
                    except Empty:
                        continue
                
                if job:
                    self._process_job(job, worker_id)
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.stats['jobs_failed'] += 1
                self._trigger_callbacks('error', {'worker_id': worker_id, 'error': str(e)})
        
        logger.debug(f"Worker {worker_id} stopped")
    
    def _process_job(self, job: ProcessingJob, worker_id: int):
        """Process a single job."""
        start_time = time.time()
        
        try:
            logger.debug(f"Worker {worker_id} processing job {job.job_id}")
            
            # Process content through aggregator
            result = asyncio.run(
                self.aggregator.process_planner_results_async(
                    job.content,
                    job.user_preferences
                )
            )
            
            # Update internal state
            self._update_cluster_state(result)
            
            processing_time = time.time() - start_time
            self.stats['processing_times'].append(processing_time)
            self.stats['jobs_processed'] += 1
            
            # Trigger callback if provided
            if job.callback:
                try:
                    job.callback(job.job_id, result)
                except Exception as e:
                    logger.error(f"Callback error for job {job.job_id}: {e}")
            
            # Trigger completion callbacks
            self._trigger_callbacks('job_completed', {
                'job_id': job.job_id,
                'result': result,
                'processing_time': processing_time,
                'worker_id': worker_id
            })
            
            logger.debug(f"Job {job.job_id} completed in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process job {job.job_id}: {e}")
            self.stats['jobs_failed'] += 1
            
            if job.callback:
                try:
                    job.callback(job.job_id, {'error': str(e)})
                except:
                    pass
            
            self._trigger_callbacks('error', {
                'job_id': job.job_id,
                'error': str(e),
                'worker_id': worker_id
            })
    
    def _batch_processor_loop(self):
        """Background loop for batch processing accumulated jobs."""
        logger.debug("Batch processor started")
        
        accumulated_jobs = []
        
        while self.processing:
            try:
                current_time = time.time()
                
                # Check if we should process a batch
                should_process_batch = (
                    len(accumulated_jobs) >= self.batch_size or
                    (accumulated_jobs and 
                     current_time - self.last_batch_time >= self.batch_interval)
                )
                
                if should_process_batch:
                    self._process_batch(accumulated_jobs)
                    accumulated_jobs.clear()
                    self.last_batch_time = current_time
                
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
        
        # Process remaining jobs
        if accumulated_jobs:
            self._process_batch(accumulated_jobs)
        
        logger.debug("Batch processor stopped")
    
    def _process_batch(self, jobs: List[ProcessingJob]):
        """Process a batch of jobs together."""
        if not jobs:
            return
        
        start_time = time.time()
        logger.debug(f"Processing batch of {len(jobs)} jobs")
        
        try:
            # Combine content from all jobs
            combined_content = self._combine_job_content(jobs)
            
            # Process through aggregator
            batch_result = asyncio.run(
                self.aggregator.process_planner_results_async(
                    combined_content,
                    jobs[0].user_preferences if jobs else None
                )
            )
            
            # Update state
            self._update_cluster_state(batch_result)
            
            # Trigger callbacks for each job
            for job in jobs:
                if job.callback:
                    try:
                        job.callback(job.job_id, batch_result)
                    except Exception as e:
                        logger.error(f"Batch callback error for job {job.job_id}: {e}")
            
            processing_time = time.time() - start_time
            self.stats['batches_processed'] += 1
            self.stats['average_batch_size'] = (
                (self.stats['average_batch_size'] * (self.stats['batches_processed'] - 1) + len(jobs)) /
                self.stats['batches_processed']
            )
            
            self._trigger_callbacks('batch_completed', {
                'job_count': len(jobs),
                'result': batch_result,
                'processing_time': processing_time
            })
            
            logger.debug(f"Batch processed in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self._trigger_callbacks('error', {'error': str(e), 'batch_size': len(jobs)})
    
    def _combine_job_content(self, jobs: List[ProcessingJob]) -> Dict[str, Any]:
        """Combine content from multiple jobs."""
        combined = {
            'breaking_news': [],
            'financial_news': [],
            'sec_filings': [],
            'general_news': [],
            'errors': []
        }
        
        for job in jobs:
            content = job.content
            for category in combined.keys():
                if category in content:
                    combined[category].extend(content[category])
        
        return combined
    
    def _update_cluster_state(self, result: AggregatorOutput):
        """Update internal cluster state with new results."""
        # Update active clusters
        for cluster in result.clusters:
            self.active_clusters[cluster.id] = cluster
            
            # Add chunks to recent cache
            for chunk in cluster.chunks:
                self.recent_chunks.append(chunk)
        
        # Clean up old clusters (keep last 100)
        if len(self.active_clusters) > 100:
            # Remove oldest clusters
            sorted_clusters = sorted(
                self.active_clusters.items(),
                key=lambda x: x[1].updated_at
            )
            for cluster_id, _ in sorted_clusters[:-100]:
                del self.active_clusters[cluster_id]
        
        # Trigger cluster update callbacks
        self._trigger_callbacks('cluster_updated', {
            'active_clusters': len(self.active_clusters),
            'new_clusters': len(result.clusters)
        })
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for specific events.
        
        Args:
            event_type: Type of event ('job_completed', 'batch_completed', 'cluster_updated', 'error')
            callback: Callback function
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.debug(f"Registered callback for {event_type}")
        else:
            logger.error(f"Unknown event type: {event_type}")
    
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Trigger callbacks for an event."""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Callback error for {event_type}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status."""
        return {
            'processing': self.processing,
            'queue_size': self.job_queue.qsize(),
            'priority_queue_size': self.priority_queue.qsize(),
            'active_workers': len([t for t in self.worker_threads if t.is_alive()]),
            'active_clusters': len(self.active_clusters),
            'recent_chunks': len(self.recent_chunks),
            'stats': self.stats.copy()
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        processing_times = list(self.stats['processing_times'])
        
        stats = self.stats.copy()
        
        if processing_times:
            stats.update({
                'avg_processing_time': sum(processing_times) / len(processing_times),
                'min_processing_time': min(processing_times),
                'max_processing_time': max(processing_times)
            })
        
        return stats
    
    def get_active_clusters(self) -> List[ContentCluster]:
        """Get list of currently active clusters."""
        return list(self.active_clusters.values())
    
    def clear_old_data(self, hours: int = 24):
        """Clear old clusters and chunks."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Remove old clusters
        old_clusters = [
            cluster_id for cluster_id, cluster in self.active_clusters.items()
            if cluster.updated_at < cutoff_time
        ]
        
        for cluster_id in old_clusters:
            del self.active_clusters[cluster_id]
        
        logger.info(f"Cleaned up {len(old_clusters)} old clusters")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.stop()
            self.active_clusters.clear()
            self.recent_chunks.clear()
            logger.info("RealtimeProcessor cleanup completed")
        except Exception as e:
            logger.error(f"Error during RealtimeProcessor cleanup: {e}")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()


# Convenience function to create and configure a real-time processor
def create_realtime_processor(aggregator: AggregatorAgent,
                             config_overrides: Optional[Dict[str, Any]] = None) -> RealtimeProcessor:
    """
    Create a configured real-time processor.
    
    Args:
        aggregator: AggregatorAgent instance
        config_overrides: Optional configuration overrides
        
    Returns:
        Configured RealtimeProcessor
    """
    default_config = {
        'batch_size': 50,
        'batch_interval': 30,
        'max_queue_size': 1000,
        'num_workers': 2,
        'enable_monitoring': True
    }
    
    if config_overrides:
        default_config.update(config_overrides)
    
    return RealtimeProcessor(
        aggregator=aggregator,
        **default_config
    )


# Example usage and monitoring
class ProcessorMonitor:
    """Simple monitoring class for RealtimeProcessor."""
    
    def __init__(self, processor: RealtimeProcessor):
        self.processor = processor
        self.start_time = time.time()
        
        # Register monitoring callbacks
        processor.register_callback('job_completed', self._on_job_completed)
        processor.register_callback('batch_completed', self._on_batch_completed)
        processor.register_callback('error', self._on_error)
    
    def _on_job_completed(self, data):
        logger.info(f"Job {data['job_id']} completed in {data['processing_time']:.2f}s")
    
    def _on_batch_completed(self, data):
        logger.info(f"Batch of {data['job_count']} jobs completed in {data['processing_time']:.2f}s")
    
    def _on_error(self, data):
        logger.warning(f"Processing error: {data['error']}")
    
    def get_uptime(self) -> float:
        return time.time() - self.start_time
    
    def print_status(self):
        status = self.processor.get_status()
        stats = self.processor.get_performance_stats()
        
        print(f"\n=== RealtimeProcessor Status ===")
        print(f"Uptime: {self.get_uptime():.1f}s")
        print(f"Processing: {status['processing']}")
        print(f"Queue Size: {status['queue_size']}")
        print(f"Active Clusters: {status['active_clusters']}")
        print(f"Jobs Processed: {stats['jobs_processed']}")
        print(f"Jobs Failed: {stats['jobs_failed']}")
        print(f"Success Rate: {stats['jobs_processed']/(stats['jobs_processed']+stats['jobs_failed'])*100:.1f}%" 
              if stats['jobs_processed'] + stats['jobs_failed'] > 0 else "N/A")


if __name__ == "__main__":
    # Example usage
    from ..aggregator.aggregator import create_aggregator_agent
    
    # Create aggregator and processor
    aggregator = create_aggregator_agent(
        gemini_api_key="dummy-key",
        database_url=None
    )
    
    processor = create_realtime_processor(aggregator)
    monitor = ProcessorMonitor(processor)
    
    # Start processing
    processor.start()
    
    # Submit some test jobs
    def result_callback(job_id, result):
        print(f"Job {job_id} callback: {len(result.get('clusters', []))} clusters")
    
    test_content = {
        'breaking_news': [],
        'financial_news': [
            {
                'title': 'Test Financial News',
                'url': 'https://example.com/test',
                'description': 'Test description',
                'source_retriever': 'test'
            }
        ],
        'sec_filings': [],
        'general_news': []
    }
    
    for i in range(5):
        processor.submit_job(
            content=test_content,
            priority=i % 3 + 1,
            callback=result_callback
        )
    
    # Wait a bit and print status
    time.sleep(5)
    monitor.print_status()
    
    # Cleanup
    processor.cleanup()
