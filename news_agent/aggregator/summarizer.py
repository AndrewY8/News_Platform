"""
Gemini API integration for cluster summarization.

This module provides AI-powered summarization of content clusters using
Google's Gemini API, with support for structured output generation,
key point extraction, and batch processing.
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time
import re
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .models import ContentCluster, ClusterSummary, SourceReference
from .config import SummarizerConfig

logger = logging.getLogger(__name__)


class GeminiSummarizer:
    """
    Gemini API-based summarization engine for content clusters.
    
    Features:
    - Google Gemini API integration
    - Structured summary generation
    - Key point extraction
    - Metadata-aware summarization
    - Batch processing support
    - Error handling and retries
    - Token limit management
    """
    
    def __init__(self, config: SummarizerConfig, api_key: Optional[str] = None):
        """
        Initialize the Gemini summarizer.
        
        Args:
            config: Summarizer configuration
            api_key: Gemini API key (if not in config)
        """
        self.config = config
        
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai is required for Gemini summarization")
       
        print(f"API KEY!!!!{api_key}")
        
        # Configure API
        api_key = api_key or getattr(config, 'api_key', None)
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=config.model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_output_tokens
            )
        )
        
        logger.info(f"Gemini summarizer initialized with model: {config.model_name}")
    
    def summarize_cluster(self, cluster: ContentCluster) -> ClusterSummary:
        """
        Generate a summary for a single content cluster.
        
        Args:
            cluster: Content cluster to summarize
            
        Returns:
            ClusterSummary object
        """
        try:
            logger.info(f"Generating summary for cluster {cluster.id} with {cluster.chunk_count} chunks")
            
            # Prepare input content
            input_text = self._prepare_cluster_input(cluster)
            
            # Generate summary using Gemini
            summary_response = self._generate_summary(input_text, cluster)
            
            # Check for API error string
            if summary_response.startswith("API_ERROR:"):
                logger.error(f"Gemini API failed for cluster {cluster.id}: {summary_response}")
                return self._create_fallback_summary(cluster, error_message=summary_response)

            # Parse response
            summary_text, key_points = self._parse_summary_response(summary_response)
            
            # Create ClusterSummary object
            cluster_summary = ClusterSummary(
                id="",  # Will be generated
                cluster_id=cluster.id,
                summary=summary_text,
                key_points=key_points,
                generated_at=datetime.datetime.now(datetime.timezone.utc),
                model_used=self.config.model_name,
                confidence=self._calculate_summary_confidence(summary_text, cluster),
                word_count=len(summary_text.split())
            )
            
            logger.info(f"Summary generated successfully: {cluster_summary.word_count} words, "
                       f"{len(key_points)} key points")
            
            return cluster_summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary for cluster {cluster.id}: {e}")
            
            # Return fallback summary
            return self._create_fallback_summary(cluster)
    
    def summarize_clusters_batch(self, clusters: List[ContentCluster]) -> List[ClusterSummary]:
        """
        Generate summaries for multiple clusters efficiently.
        
        Args:
            clusters: List of content clusters
            
        Returns:
            List of ClusterSummary objects
        """
        if not clusters:
            return []
        
        logger.info(f"Generating summaries for {len(clusters)} clusters")
        
        summaries = []
        batch_size = self.config.batch_size
        
        # Process in batches to respect API limits
        for i in range(0, len(clusters), batch_size):
            batch = clusters[i:i + batch_size]
            batch_summaries = []
            
            for cluster in batch:
                try:
                    summary = self.summarize_cluster(cluster)
                    batch_summaries.append(summary)
                    
                    # Add delay to respect rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Failed to summarize cluster {cluster.id}: {e}")
                    # Add fallback summary
                    fallback = self._create_fallback_summary(cluster)
                    batch_summaries.append(fallback)
            
            summaries.extend(batch_summaries)
            
            # Longer delay between batches
            if i + batch_size < len(clusters):
                time.sleep(2.0)
        
        logger.info(f"Batch summarization completed: {len(summaries)} summaries generated")
        return summaries
    
    async def summarize_clusters_async(self, clusters: List[ContentCluster]) -> List[ClusterSummary]:
        """
        Asynchronously generate summaries for clusters.
        
        Args:
            clusters: List of content clusters
            
        Returns:
            List of ClusterSummary objects
        """
        if not clusters:
            return []
        
        logger.info(f"Generating summaries asynchronously for {len(clusters)} clusters")
        
        # Create tasks for each cluster
        tasks = []
        for cluster in clusters:
            task = self._summarize_cluster_async(cluster)
            tasks.append(task)
        
        # Execute with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.config.batch_size)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        bounded_tasks = [bounded_task(task) for task in tasks]
        summaries = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        # Handle exceptions
        result_summaries = []
        for i, summary in enumerate(summaries):
            if isinstance(summary, Exception):
                logger.error(f"Async summarization failed for cluster {clusters[i].id}: {summary}")
                fallback = self._create_fallback_summary(clusters[i])
                result_summaries.append(fallback)
            else:
                result_summaries.append(summary)
        
        logger.info(f"Async summarization completed: {len(result_summaries)} summaries")
        return result_summaries
    
    async def _summarize_cluster_async(self, cluster: ContentCluster) -> ClusterSummary:
        """Async wrapper for cluster summarization."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.summarize_cluster, cluster)
    
    def _prepare_cluster_input(self, cluster: ContentCluster) -> str:
        """
        Prepare input text for summarization from cluster content.
        
        Args:
            cluster: Content cluster
            
        Returns:
            Formatted input text for the model
        """
        # Collect content from all chunks
        chunk_contents = []
        
        for chunk in cluster.chunks:
            content = chunk.processed_content or chunk.content
            
            # Add metadata context
            chunk_info = {
                'title': chunk.metadata.title,
                'source': chunk.metadata.source,
                'timestamp': chunk.metadata.timestamp.isoformat(),
                'content': content[:500]  # Limit content length
            }
            
            chunk_contents.append(chunk_info)
        
        # Sort by timestamp (most recent first)
        chunk_contents.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Format for model input
        formatted_input = self._format_input_for_model(chunk_contents, cluster)
        
        return formatted_input
    
    def _format_input_for_model(self, chunk_contents: List[Dict[str, Any]], 
                               cluster: ContentCluster) -> str:
        """
        Format cluster content for Gemini model input.
        
        Args:
            chunk_contents: List of chunk content dictionaries
            cluster: Content cluster
            
        Returns:
            Formatted input string
        """
        # Create context about the cluster
        context_lines = [
            "CLUSTER SUMMARY REQUEST",
            f"Cluster contains {len(chunk_contents)} news articles on related topics.",
        ]
        
        if cluster.metadata.primary_ticker:
            context_lines.append(f"Primary ticker: {cluster.metadata.primary_ticker}")
        
        if cluster.metadata.topics:
            context_lines.append(f"Topics: {', '.join(cluster.metadata.topics)}")
        
        context_lines.extend([
            "",
            "Please analyze these articles and provide:",
            "1. A comprehensive summary (2-3 paragraphs)",
            "2. Key points (3-5 bullet points)",
            "3. Focus on factual information and avoid speculation",
            "",
            "ARTICLES:"
        ])
        
        # Add article contents
        for i, chunk_info in enumerate(chunk_contents, 1):
            context_lines.extend([
                f"\n--- Article {i} ---",
                f"Title: {chunk_info['title']}",
                f"Source: {chunk_info['source']}",
                f"Published: {chunk_info['timestamp'][:10]}",  # Just date
                f"Content: {chunk_info['content']}",
                ""
            ])
        
        return "\n".join(context_lines)
    
    def _generate_summary(self, input_text: str, cluster: ContentCluster) -> str:
        """
        Generate summary using Gemini API with retry logic.
        
        Args:
            input_text: Formatted input text
            cluster: Content cluster (for context)
            
        Returns:
            Generated summary text
        """
        for attempt in range(self.config.retry_attempts):
            try:
                # Check token limits
                if len(input_text) > self.config.max_input_tokens * 4:  # Rough estimate
                    input_text = input_text[:self.config.max_input_tokens * 4]
                    logger.warning(f"Truncated input for cluster {cluster.id} due to token limit")
                
                # Generate content
                response = self.model.generate_content(
                    input_text,
                    request_options={'timeout': self.config.timeout}
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    raise ValueError("Empty response from Gemini API")
                
            except (ResourceExhausted, ServiceUnavailable) as e:
                logger.warning(f"Gemini API rate limit or unavailability encountered (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for Gemini API: {e}")
                    return "API_ERROR: " + str(e) # Return a specific error string
            except Exception as e:
                logger.warning(f"Summarization attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.retry_attempts - 1:
                    # Exponential backoff
                    delay = self.config.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise e
    
    def _parse_summary_response(self, response_text: str) -> Tuple[str, List[str]]:
        """
        Parse Gemini response to extract summary and key points.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Tuple of (summary_text, key_points_list)
        """
        lines = response_text.strip().split('\n')
        
        summary_lines = []
        key_points = []
        current_section = "summary"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect key points section
            if any(marker in line.lower() for marker in ['key points', 'main points', 'highlights']):
                current_section = "key_points"
                continue
            
            if current_section == "summary":
                # Skip lines that look like headers
                if not (line.startswith('#') or line.isupper()):
                    summary_lines.append(line)
            
            elif current_section == "key_points":
                # Extract bullet points
                if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    # Clean up bullet point
                    clean_point = re.sub(r'^[•\-\*\d\.]\s*', '', line).strip()
                    if clean_point:
                        key_points.append(clean_point)
        
        # Join summary lines
        summary_text = ' '.join(summary_lines)
        
        # If no key points found, extract from summary
        if not key_points and summary_text:
            key_points = self._extract_key_points_from_summary(summary_text)
        
        return summary_text, key_points
    
    def _extract_key_points_from_summary(self, summary_text: str) -> List[str]:
        """Extract key points from summary text as fallback."""
        sentences = re.split(r'[.!?]+', summary_text)
        
        # Take first few meaningful sentences as key points
        key_points = []
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short sentences
                key_points.append(sentence)
        
        return key_points[:3]  # Limit to 3 points
    
    def _calculate_summary_confidence(self, summary_text: str, cluster: ContentCluster) -> float:
        """
        Calculate confidence score for generated summary.
        
        Args:
            summary_text: Generated summary
            cluster: Original cluster
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 1.0
        
        # Reduce confidence for very short summaries
        word_count = len(summary_text.split())
        if word_count < 50:
            confidence *= 0.7
        elif word_count < 100:
            confidence *= 0.9
        
        # Reduce confidence for clusters with very few sources
        if cluster.chunk_count < 3:
            confidence *= 0.8
        
        # Reduce confidence if summary seems generic
        generic_phrases = ['according to reports', 'it is reported', 'sources say']
        generic_count = sum(1 for phrase in generic_phrases if phrase in summary_text.lower())
        if generic_count > 2:
            confidence *= 0.8
        
        return max(0.3, confidence)  # Minimum confidence threshold
    
    def _create_fallback_summary(self, cluster: ContentCluster) -> ClusterSummary:
        """
        Create a fallback summary when AI generation fails.
        
        Args:
            cluster: Content cluster
            
        Returns:
            Fallback ClusterSummary
        """
        # Create basic summary from titles and metadata
        titles = [chunk.metadata.title for chunk in cluster.chunks[:3]]
        
        fallback_text = f"This cluster contains {cluster.chunk_count} related articles"
        
        if cluster.metadata.primary_ticker:
            fallback_text += f" about {cluster.metadata.primary_ticker}"
        
        if cluster.metadata.topics:
            fallback_text += f" covering {', '.join(cluster.metadata.topics[:2])}"
        
        fallback_text += f". Recent articles include: {'; '.join(titles[:2])}."
        
        # Extract key points from titles
        key_points = titles[:3] if len(titles) >= 3 else titles
        
        return ClusterSummary(
            id="",  # Will be generated
            cluster_id=cluster.id,
            summary=fallback_text,
            key_points=key_points,
            generated_at=datetime.utcnow(),
            model_used="fallback",
            confidence=0.3,  # Low confidence for fallback
            word_count=len(fallback_text.split())
        )
    
    def create_structured_output(self, cluster: ContentCluster, 
                               summary: ClusterSummary) -> Dict[str, Any]:
        """
        Create structured output combining cluster and summary data.
        
        Args:
            cluster: Content cluster
            summary: Generated summary
            
        Returns:
            Structured output dictionary ready for database/API
        """
        # Get source references
        sources = cluster.get_sources()
        
        output = {
            "id": cluster.id,
            "summary": summary.summary,
            "sources": [source.to_dict() for source in sources],
            "metadata": {
                "ticker": cluster.metadata.primary_ticker,
                "topics": cluster.metadata.topics,
                "source_count": cluster.source_count,
                "cluster_size": cluster.chunk_count,
                "confidence_score": summary.confidence,
                "generated_at": summary.generated_at.isoformat(),
                "model_used": summary.model_used
            },
            "key_points": summary.key_points,
            "cluster_score": getattr(cluster.metadata, 'final_score', None)
        }
        
        return output
    
    def get_summarization_stats(self, summaries: List[ClusterSummary]) -> Dict[str, Any]:
        """
        Get statistics about summarization results.
        
        Args:
            summaries: List of generated summaries
            
        Returns:
            Dictionary of summarization statistics
        """
        if not summaries:
            return {}
        
        word_counts = [s.word_count for s in summaries]
        confidence_scores = [s.confidence for s in summaries]
        key_point_counts = [len(s.key_points) for s in summaries]
        
        models_used = {}
        for summary in summaries:
            models_used[summary.model_used] = models_used.get(summary.model_used, 0) + 1
        
        return {
            'total_summaries': len(summaries),
            'word_count_stats': {
                'min': min(word_counts),
                'max': max(word_counts),
                'mean': sum(word_counts) / len(word_counts),
                'median': sorted(word_counts)[len(word_counts) // 2]
            },
            'confidence_stats': {
                'min': min(confidence_scores),
                'max': max(confidence_scores),
                'mean': sum(confidence_scores) / len(confidence_scores)
            },
            'key_points_stats': {
                'min': min(key_point_counts),
                'max': max(key_point_counts),
                'mean': sum(key_point_counts) / len(key_point_counts)
            },
            'models_used': models_used
        }
