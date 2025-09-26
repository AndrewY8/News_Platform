"""
Cluster scoring system for the News Aggregator.

This module implements multi-factor scoring for content clusters based on:
- Recency (time-based decay)
- Source reliability (tier-based scoring)
- User relevance (ticker/topic matching)
- Breaking news detection and boosting
- Source diversity bonuses
"""

import logging
import math
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from .models import ContentCluster, ContentChunk, SourceType, ReliabilityTier
from .config import ScoringConfig

logger = logging.getLogger(__name__)


class ClusterScorer:
    """
    Multi-factor scoring system for content clusters.
    
    Features:
    - Time-based recency scoring with decay
    - Source reliability weighted scoring
    - User preference matching (tickers/topics)
    - Breaking news detection and boosting
    - Source diversity rewards
    - Configurable scoring weights
    """
    
    def __init__(self, config: ScoringConfig):
        """
        Initialize the cluster scorer.
        
        Args:
            config: Scoring configuration parameters
        """
        self.config = config
        
        # Validate configuration
        if not self._validate_config():
            raise ValueError("Invalid scoring configuration")
    
    def _validate_config(self) -> bool:
        """Validate scoring configuration."""
        total_weight = (
            self.config.recency_weight + 
            self.config.reliability_weight + 
            self.config.relevance_weight
        )
        
        if abs(total_weight - 1.0) > 0.01:
            logger.error(f"Scoring weights must sum to 1.0, got {total_weight}")
            return False
        
        return True
    
    def score_clusters(self, clusters: List[ContentCluster], 
                      user_preferences: Optional[Dict[str, Any]] = None) -> List[ContentCluster]:
        """
        Score all clusters and sort by relevance.
        
        Args:
            clusters: List of content clusters to score
            user_preferences: Optional user preferences for relevance scoring
            
        Returns:
            List of clusters sorted by score (highest first)
        """
        if not clusters:
            return []
        
        logger.info(f"Scoring {len(clusters)} clusters")
        
        # Calculate scores for all clusters
        scored_clusters = []
        
        for cluster in clusters:
            score = self.calculate_cluster_score(cluster, user_preferences)
            
            # Store score in cluster metadata for later use
            cluster.metadata.__dict__['final_score'] = score
            
            scored_clusters.append((score, cluster))
        
        # Sort by score (descending)
        scored_clusters.sort(key=lambda x: x[0], reverse=True)
        
        # Extract clusters and log top scores
        result_clusters = [cluster for score, cluster in scored_clusters]
        
        logger.info("Top cluster scores:")
        for i, (score, cluster) in enumerate(scored_clusters[:5]):
            logger.info(f"  {i+1}. Score: {score:.3f}, Chunks: {cluster.chunk_count}, "
                       f"Primary topic: {cluster.metadata.topics[0] if cluster.metadata.topics else 'N/A'}")
        
        return result_clusters
    
    def calculate_cluster_score(self, cluster: ContentCluster, 
                              user_preferences: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate comprehensive score for a single cluster.
        
        Args:
            cluster: Content cluster to score
            user_preferences: Optional user preferences
            
        Returns:
            Normalized score between 0 and 1
        """
        # Calculate component scores
        recency_score = self._calculate_recency_score(cluster)
        reliability_score = self._calculate_reliability_score(cluster)
        relevance_score = self._calculate_relevance_score(cluster, user_preferences)
        
        # Calculate base score using configured weights
        base_score = (
            recency_score * self.config.recency_weight +
            reliability_score * self.config.reliability_weight +
            relevance_score * self.config.relevance_weight
        )
        
        # Apply multipliers and bonuses
        final_score = base_score
        
        # Breaking news boost
        if self._is_breaking_news_cluster(cluster):
            final_score *= self.config.breaking_news_boost
            logger.debug(f"Applied breaking news boost to cluster {cluster.id}")
        
        # Source diversity bonus
        diversity_bonus = self._calculate_source_diversity_bonus(cluster)
        final_score += diversity_bonus
        
        # Ensure score stays within [0, 1] range
        final_score = max(0.0, min(1.0, final_score))
        
        return final_score
    
    def _calculate_recency_score(self, cluster: ContentCluster) -> float:
        """
        Calculate recency score based on cluster timestamps.
        
        Args:
            cluster: Content cluster
            
        Returns:
            Recency score between 0 and 1
        """
        if not cluster.chunks:
            return 0.0
        
        # Get the most recent timestamp from cluster chunks
        most_recent = max(chunk.metadata.timestamp for chunk in cluster.chunks)
        
        # Calculate age in hours
        age_hours = (datetime.utcnow() - most_recent).total_seconds() / 3600
        
        # Apply exponential decay
        decay_factor = math.exp(-age_hours / self.config.time_decay_hours)
        
        # Ensure minimum score
        recency_score = max(self.config.max_time_decay, decay_factor)
        
        return recency_score
    
    def _calculate_reliability_score(self, cluster: ContentCluster) -> float:
        """
        Calculate reliability score based on source quality.
        
        Args:
            cluster: Content cluster
            
        Returns:
            Reliability score between 0 and 1
        """
        if not cluster.chunks:
            return 0.0
        
        # Collect reliability scores from all chunks
        reliability_scores = []
        
        for chunk in cluster.chunks:
            score = chunk.metadata.source_reliability_score
            reliability_scores.append(score)
        
        # Calculate weighted average (could weight by content length, recency, etc.)
        # For now, using simple average
        avg_reliability = sum(reliability_scores) / len(reliability_scores)
        
        # Bonus for having multiple high-quality sources
        high_quality_sources = sum(1 for score in reliability_scores if score >= 0.8)
        diversity_bonus = min(0.1, high_quality_sources * 0.02)
        
        reliability_score = min(1.0, avg_reliability + diversity_bonus)
        
        return reliability_score
    
    def _calculate_relevance_score(self, cluster: ContentCluster, 
                                 user_preferences: Optional[Dict[str, Any]]) -> float:
        """
        Calculate relevance score based on user preferences.
        
        Args:
            cluster: Content cluster
            user_preferences: User preferences dictionary
            
        Returns:
            Relevance score between 0 and 1
        """
        if not user_preferences:
            # Default relevance for general users
            return self._calculate_default_relevance(cluster)
        
        relevance_score = 0.0
        
        # Ticker relevance
        watchlist = user_preferences.get('watchlist', [])
        if watchlist and cluster.metadata.primary_ticker:
            if cluster.metadata.primary_ticker.upper() in [ticker.upper() for ticker in watchlist]:
                relevance_score += 0.5
                logger.debug(f"Ticker match: {cluster.metadata.primary_ticker}")
        
        # Topic relevance
        preferred_topics = user_preferences.get('topics', [])
        if preferred_topics and cluster.metadata.topics:
            topic_overlap = set(cluster.metadata.topics) & set(preferred_topics)
            if topic_overlap:
                relevance_score += 0.3 * len(topic_overlap) / len(preferred_topics)
                logger.debug(f"Topic overlap: {topic_overlap}")
        
        # Keyword relevance
        keywords = user_preferences.get('keywords', [])
        if keywords:
            keyword_score = self._calculate_keyword_relevance(cluster, keywords)
            relevance_score += keyword_score * 0.2
        
        # Industry/sector relevance
        sectors = user_preferences.get('sectors', [])
        if sectors:
            sector_score = self._calculate_sector_relevance(cluster, sectors)
            relevance_score += sector_score * 0.1
        
        # Cap at 1.0
        return min(1.0, relevance_score)
    
    def _calculate_default_relevance(self, cluster: ContentCluster) -> float:
        """Calculate default relevance for general users."""
        relevance_score = 0.5  # Base relevance
        
        # Boost for breaking news
        if self._is_breaking_news_cluster(cluster):
            relevance_score += 0.2
        
        # Boost for financial news
        financial_types = {SourceType.FINANCIAL_NEWS, SourceType.SEC_FILING}
        if any(st in financial_types for st in cluster.metadata.source_types):
            relevance_score += 0.1
        
        # Boost for clusters with tickers (indicates company-specific news)
        if cluster.metadata.primary_ticker:
            relevance_score += 0.1
        
        return min(1.0, relevance_score)
    
    def _calculate_keyword_relevance(self, cluster: ContentCluster, keywords: List[str]) -> float:
        """Calculate relevance based on keyword matching."""
        if not keywords or not cluster.chunks:
            return 0.0
        
        total_matches = 0
        total_possible = len(keywords) * len(cluster.chunks)
        
        for chunk in cluster.chunks:
            content = (chunk.processed_content or chunk.content).lower()
            title = chunk.metadata.title.lower()
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Weight title matches more than content matches
                if keyword_lower in title:
                    total_matches += 2
                elif keyword_lower in content:
                    total_matches += 1
        
        return min(1.0, total_matches / max(1, total_possible))
    
    def _calculate_sector_relevance(self, cluster: ContentCluster, sectors: List[str]) -> float:
        """Calculate relevance based on sector/industry matching."""
        # Simple keyword-based sector matching
        # In a real system, this would use more sophisticated entity recognition
        
        sector_keywords = {
            'technology': ['tech', 'software', 'ai', 'artificial intelligence', 'cloud', 'saas'],
            'healthcare': ['health', 'medical', 'pharma', 'biotech', 'drug', 'treatment'],
            'finance': ['bank', 'financial', 'fintech', 'payment', 'loan', 'credit'],
            'energy': ['oil', 'gas', 'renewable', 'solar', 'wind', 'energy', 'power'],
            'retail': ['retail', 'consumer', 'shopping', 'ecommerce', 'store'],
            'automotive': ['auto', 'car', 'vehicle', 'tesla', 'ford', 'gm']
        }
        
        relevance = 0.0
        
        for sector in sectors:
            sector_lower = sector.lower()
            keywords = sector_keywords.get(sector_lower, [sector_lower])
            
            sector_score = self._calculate_keyword_relevance(cluster, keywords)
            relevance += sector_score
        
        return min(1.0, relevance / len(sectors)) if sectors else 0.0
    
    def _is_breaking_news_cluster(self, cluster: ContentCluster) -> bool:
        """
        Determine if cluster represents breaking news.
        
        Args:
            cluster: Content cluster to check
            
        Returns:
            True if cluster is breaking news
        """
        # Check if any chunks are classified as breaking news
        if SourceType.BREAKING_NEWS in cluster.metadata.source_types:
            return True
        
        # Check for breaking news indicators in titles/content
        breaking_indicators = [
            'breaking', 'urgent', 'developing', 'just in', 'live update', 
            'alert', 'flash', 'emergency', 'immediate'
        ]
        
        for chunk in cluster.chunks:
            title_lower = chunk.metadata.title.lower()
            content_lower = (chunk.processed_content or chunk.content)[:200].lower()
            
            if any(indicator in title_lower or indicator in content_lower 
                   for indicator in breaking_indicators):
                return True
        
        # Check recency - very recent clusters might be breaking
        if cluster.chunks:
            most_recent = max(chunk.metadata.timestamp for chunk in cluster.chunks)
            age_minutes = (datetime.utcnow() - most_recent).total_seconds() / 60
            
            if age_minutes < 30:  # Less than 30 minutes old
                return True
        
        return False
    
    def _calculate_source_diversity_bonus(self, cluster: ContentCluster) -> float:
        """
        Calculate bonus for source diversity within cluster.
        
        Args:
            cluster: Content cluster
            
        Returns:
            Diversity bonus (0 to configured maximum)
        """
        if not cluster.chunks or len(cluster.chunks) < 2:
            return 0.0
        
        # Count unique sources
        sources = set(chunk.metadata.source for chunk in cluster.chunks)
        unique_sources = len(sources)
        
        # Count different source types
        source_types = set(chunk.metadata.source_type for chunk in cluster.chunks)
        type_diversity = len(source_types)
        
        # Calculate diversity score
        # Bonus for having multiple sources and source types
        source_bonus = min(0.05, (unique_sources - 1) * 0.01)
        type_bonus = min(0.05, (type_diversity - 1) * 0.02)
        
        total_bonus = source_bonus + type_bonus
        
        # Apply configured maximum
        return min(self.config.source_diversity_bonus, total_bonus)
    
    def get_top_clusters(self, clusters: List[ContentCluster], 
                        count: Optional[int] = None, 
                        user_preferences: Optional[Dict[str, Any]] = None) -> List[ContentCluster]:
        """
        Get top-scored clusters.
        
        Args:
            clusters: List of clusters to score and rank
            count: Number of top clusters to return (None for all)
            user_preferences: Optional user preferences
            
        Returns:
            Top clusters sorted by score
        """
        scored_clusters = self.score_clusters(clusters, user_preferences)
        
        if count is None:
            return scored_clusters
        
        return scored_clusters[:count]
    
    def get_cluster_score_breakdown(self, cluster: ContentCluster, 
                                  user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Get detailed score breakdown for a cluster.
        
        Args:
            cluster: Cluster to analyze
            user_preferences: Optional user preferences
            
        Returns:
            Dictionary with score components
        """
        recency_score = self._calculate_recency_score(cluster)
        reliability_score = self._calculate_reliability_score(cluster)
        relevance_score = self._calculate_relevance_score(cluster, user_preferences)
        
        base_score = (
            recency_score * self.config.recency_weight +
            reliability_score * self.config.reliability_weight +
            relevance_score * self.config.relevance_weight
        )
        
        is_breaking = self._is_breaking_news_cluster(cluster)
        diversity_bonus = self._calculate_source_diversity_bonus(cluster)
        
        final_score = base_score
        if is_breaking:
            final_score *= self.config.breaking_news_boost
        final_score += diversity_bonus
        final_score = max(0.0, min(1.0, final_score))
        
        return {
            'recency_score': recency_score,
            'reliability_score': reliability_score,
            'relevance_score': relevance_score,
            'base_score': base_score,
            'is_breaking_news': is_breaking,
            'breaking_news_multiplier': self.config.breaking_news_boost if is_breaking else 1.0,
            'diversity_bonus': diversity_bonus,
            'final_score': final_score,
            'weights': {
                'recency': self.config.recency_weight,
                'reliability': self.config.reliability_weight,
                'relevance': self.config.relevance_weight
            }
        }
    
    def get_scoring_stats(self, clusters: List[ContentCluster]) -> Dict[str, Any]:
        """
        Get statistics about cluster scoring.
        
        Args:
            clusters: List of scored clusters
            
        Returns:
            Dictionary of scoring statistics
        """
        if not clusters:
            return {}
        
        scores = []
        breaking_count = 0
        source_diversity_scores = []
        
        for cluster in clusters:
            if hasattr(cluster.metadata, 'final_score'):
                scores.append(cluster.metadata.__dict__['final_score'])
            
            if self._is_breaking_news_cluster(cluster):
                breaking_count += 1
            
            diversity_bonus = self._calculate_source_diversity_bonus(cluster)
            source_diversity_scores.append(diversity_bonus)
        
        return {
            'total_clusters': len(clusters),
            'breaking_news_clusters': breaking_count,
            'score_stats': {
                'min': min(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'mean': sum(scores) / len(scores) if scores else 0,
                'median': sorted(scores)[len(scores) // 2] if scores else 0
            },
            'diversity_bonus_stats': {
                'min': min(source_diversity_scores),
                'max': max(source_diversity_scores),
                'mean': sum(source_diversity_scores) / len(source_diversity_scores)
            }
        }
