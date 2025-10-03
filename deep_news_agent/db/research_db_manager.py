"""
Research Database Manager - Handles database operations for the research pipeline
Integrates with the orchestrator pipeline to store companies, articles, topics, and relationships
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np

from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

# Import your existing types
from ..agents.interfaces import Topic, CompanyContext, SearchResult, RankedTopic, Subtopic


@dataclass
class StoredArticle:
    """Represents an article stored in the database"""
    id: int
    title: str
    url: str
    content: str
    source: str
    relevance_score: float


@dataclass
class StoredTopic:
    """Represents a topic stored in the database"""
    id: int
    company_id: int
    name: str
    description: str
    final_score: Optional[float] = None


class ResearchDBManager:
    """Database manager specifically designed for the research orchestrator pipeline"""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger = logging.getLogger(__name__)

        # Initialize embedding model for articles
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    @staticmethod
    def _sanitize_for_json(obj):
        """Convert numpy types and other non-serializable types to JSON-safe types"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating, np.float32, np.float64, np.float16)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int32, np.int64, np.int16, np.int8)):
            return int(obj)
        if isinstance(obj, dict):
            return {k: ResearchDBManager._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ResearchDBManager._sanitize_for_json(v) for v in obj]
        return obj

    # ============================================================================
    # COMPANY OPERATIONS
    # ============================================================================

    def create_or_get_company(self, company_context: CompanyContext) -> int:
        """
        Create a company record or get existing one
        Returns the company ID
        """
        try:
            # Check if company exists
            existing = self.supabase.table("companies").select("id").eq("name", company_context.name).execute()

            if existing.data:
                company_id = existing.data[0]["id"]
                self.logger.info(f"Found existing company: {company_context.name} (ID: {company_id})")
                return company_id

            # Create new company
            company_data = {
                "name": company_context.name,
                "business_areas": company_context.business_areas,
                "current_status": self._sanitize_for_json(company_context.current_status)
            }

            result = self.supabase.table("companies").insert(company_data).execute()
            company_id = result.data[0]["id"]

            self.logger.info(f"Created new company: {company_context.name} (ID: {company_id})")
            return company_id

        except Exception as e:
            self.logger.error(f"Error creating/getting company {company_context.name}: {e}")
            raise

    # ============================================================================
    # ARTICLE OPERATIONS
    # ============================================================================

    def store_search_results(self, search_results: List[SearchResult], search_query: str,
                           iteration: int) -> List[StoredArticle]:
        """
        Store search results as articles in the database
        Returns list of stored article objects with IDs
        """
        stored_articles = []

        for result in search_results:
            try:
                # Generate embedding for the content
                embedding = self.embedding_model.encode(result.content[:1000]).tolist()  # Limit content for embedding

                # Extract domain from URL if available
                source_domain = None
                if hasattr(result, 'url') and result.url:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(result.url)
                        source_domain = parsed.netloc.replace('www.', '')
                    except:
                        source_domain = None

                article_data = {
                    "title": result.title if hasattr(result, 'title') else result.content[:100],
                    "url": result.url if hasattr(result, 'url') else f"no-url-{datetime.now().isoformat()}",
                    "content": result.content,
                    "source": result.source,
                    "source_domain": source_domain,
                    "published_date": result.timestamp.isoformat() if result.timestamp else None,
                    "search_query": search_query,
                    "relevance_score": getattr(result, 'relevance_score', 0.5),
                    "pipeline_iteration": iteration,
                    "embedding": embedding
                }

                # Handle potential duplicates by URL
                existing = self.supabase.table("articles").select("id").eq("url", article_data["url"]).execute()

                if existing.data:
                    # Article already exists, return existing record
                    article_id = existing.data[0]["id"]
                    self.logger.debug(f"Article already exists: {article_data['title'][:50]}... (ID: {article_id})")
                else:
                    # Insert new article
                    result = self.supabase.table("articles").insert(article_data).execute()
                    article_id = result.data[0]["id"]
                    self.logger.debug(f"Stored new article: {article_data['title'][:50]}... (ID: {article_id})")

                stored_articles.append(StoredArticle(
                    id=article_id,
                    title=article_data["title"],
                    url=article_data["url"],
                    content=article_data["content"],
                    source=article_data["source"],
                    relevance_score=article_data["relevance_score"]
                ))

            except Exception as e:
                self.logger.error(f"Error storing article: {e}")
                continue

        self.logger.info(f"Stored {len(stored_articles)} articles from search results")
        return stored_articles

    # ============================================================================
    # TOPIC OPERATIONS
    # ============================================================================

    def store_extracted_topics(self, topics: List[Topic], company_id: int,
                             iteration: int, source_articles: List[StoredArticle]) -> List[StoredTopic]:
        """
        Store extracted topics and create relationships with source articles
        """
        stored_topics = []

        for topic in topics:
            try:
                topic_data = {
                    "company_id": company_id,
                    "name": topic.name,
                    "description": topic.description,
                    "business_impact": topic.business_impact,
                    "confidence": float(topic.confidence),
                    "urgency": topic.urgency,
                    "extraction_date": topic.extraction_date.isoformat(),
                    "pipeline_iteration": iteration,
                    "subtopics": self._serialize_subtopics(topic.subtopics)  # Store as JSON array
                }

                # Insert topic
                result = self.supabase.table("topics").insert(topic_data).execute()
                topic_id = result.data[0]["id"]

                # Create article-topic relationships
                # For now, link all source articles to this topic with equal contribution
                self._create_article_topic_relationships(source_articles, topic_id, topic.sources)

                stored_topics.append(StoredTopic(
                    id=topic_id,
                    company_id=company_id,
                    name=topic.name,
                    description=topic.description
                ))

                self.logger.debug(f"Stored topic: {topic.name} (ID: {topic_id})")

            except Exception as e:
                self.logger.error(f"Error storing topic {topic.name}: {e}")
                continue

        self.logger.info(f"Stored {len(stored_topics)} topics for iteration {iteration}")
        return stored_topics

    def update_topic_rankings(self, ranked_topics: List[RankedTopic]) -> None:
        """
        Update topics with their final ranking scores
        """
        try:
            for ranked_topic in ranked_topics:
                # Find the topic in database by name and company
                # This is a limitation - we need a better way to match topics
                topic_data = ranked_topic.topic

                update_data = {
                    "final_score": float(ranked_topic.final_score),
                    "impact_score": float(ranked_topic.impact_score),
                    "recency_score": float(ranked_topic.recency_score),
                    "relatedness_score": float(ranked_topic.relatedness_score),
                    "credibility_score": float(ranked_topic.credibility_score),
                    "rank_position": ranked_topic.rank
                }

                # Update by topic name (this is imperfect, but workable for now)
                result = self.supabase.table("topics").update(update_data).eq("name", topic_data.name).execute()

                if result.data:
                    self.logger.debug(f"Updated rankings for topic: {topic_data.name}")
                else:
                    self.logger.warning(f"Could not find topic to update rankings: {topic_data.name}")

        except Exception as e:
            self.logger.error(f"Error updating topic rankings: {e}")

    def _create_article_topic_relationships(self, articles: List[StoredArticle],
                                          topic_id: int, topic_sources: List[str]) -> None:
        """
        Create many-to-many relationships between articles and topics
        """
        try:
            relationships = []

            for article in articles:
                # Simple heuristic: if article URL is in topic sources, higher contribution
                contribution_strength = 0.8 if article.url in topic_sources else 0.3

                relationships.append({
                    "article_id": article.id,
                    "topic_id": topic_id,
                    "contribution_strength": contribution_strength,
                    "extraction_method": "batch_extraction"
                })

            if relationships:
                self.supabase.table("article_topics").insert(relationships).execute()
                self.logger.debug(f"Created {len(relationships)} article-topic relationships")

        except Exception as e:
            self.logger.error(f"Error creating article-topic relationships: {e}")

    def store_single_topic(self, topic: Topic, company_id: int, iteration: int) -> StoredTopic:
        """
        Store a single topic and return the stored topic with ID
        """
        try:
            topic_data = {
                "company_id": company_id,
                "name": topic.name,
                "description": topic.description,
                "business_impact": topic.business_impact,
                "confidence": float(topic.confidence),
                "urgency": topic.urgency,
                "extraction_date": topic.extraction_date.isoformat(),
                "pipeline_iteration": iteration,
                "subtopics": self._serialize_subtopics(topic.subtopics)  # Store as JSON array
            }

            # Insert topic
            result = self.supabase.table("topics").insert(topic_data).execute()
            topic_id = result.data[0]["id"]

            self.logger.debug(f"Stored topic: {topic.name} (ID: {topic_id})")

            return StoredTopic(
                id=topic_id,
                company_id=company_id,
                name=topic.name,
                description=topic.description
            )

        except Exception as e:
            self.logger.error(f"Error storing topic {topic.name}: {e}")
            raise

    def store_article_topic_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        """
        Store article-topic relationships in bulk
        """
        try:
            if relationships:
                self.supabase.table("article_topics").insert(relationships).execute()
                self.logger.debug(f"Stored {len(relationships)} article-topic relationships")

        except Exception as e:
            self.logger.error(f"Error storing article-topic relationships: {e}")
            raise

    # ============================================================================
    # QUERY OPERATIONS
    # ============================================================================

    def get_company_topics(self, company_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all topics for a company with their associated articles
        """
        try:
            query = self.supabase.table("topics").select("""
                id, name, description, business_impact, confidence, urgency,
                final_score, rank_position, subtopics, extraction_date,
                article_topics(
                    contribution_strength,
                    articles(id, title, url, source, published_date, relevance_score)
                )
            """).eq("companies.name", company_name).order("rank_position", desc=False)

            if limit:
                query = query.limit(limit)

            result = query.execute()
            return result.data

        except Exception as e:
            self.logger.error(f"Error getting topics for company {company_name}: {e}")
            return []

    def get_topic_articles(self, topic_id: int) -> List[Dict[str, Any]]:
        """
        Get all articles associated with a specific topic
        """
        try:
            result = self.supabase.table("article_topics").select("""
                contribution_strength,
                articles(id, title, url, content, source, published_date, relevance_score)
            """).eq("topic_id", topic_id).order("contribution_strength", desc=True).execute()

            return result.data

        except Exception as e:
            self.logger.error(f"Error getting articles for topic {topic_id}: {e}")
            return []

    def get_company_research_summary(self, company_name: str) -> Dict[str, Any]:
        """
        Get a summary of all research data for a company
        """
        try:
            # Use the view we created in the schema
            result = self.supabase.table("company_topic_summary").select("*").eq("company_name", company_name).execute()

            if result.data:
                return result.data[0]
            else:
                return {"company_name": company_name, "total_topics": 0}

        except Exception as e:
            self.logger.error(f"Error getting research summary for {company_name}: {e}")
            return {"company_name": company_name, "error": str(e)}

    # ============================================================================
    # SUBTOPIC QUERY OPERATIONS
    # ============================================================================

    def get_topics_with_subtopics(self, company_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get topics that have subtopics for a company using the enhanced view
        """
        try:
            query = self.supabase.table("topic_with_subtopics").select("""
                topic_id, topic_name, company_id, urgency, confidence, final_score,
                extraction_date, subtopic_count, subtopics
            """).eq("companies.name", company_name).gt("subtopic_count", 0).order("final_score", desc=True)

            if limit:
                query = query.limit(limit)

            result = query.execute()
            return result.data

        except Exception as e:
            self.logger.error(f"Error getting topics with subtopics for {company_name}: {e}")
            return []

    def get_subtopic_details(self, topic_id: int) -> List[Dict[str, Any]]:
        """
        Get detailed information about all subtopics for a specific topic
        """
        try:
            result = self.supabase.table("subtopic_detail").select("*").eq("topic_id", topic_id).execute()
            return result.data

        except Exception as e:
            self.logger.error(f"Error getting subtopic details for topic {topic_id}: {e}")
            return []

    def get_company_subtopic_analysis(self, company_name: str) -> Dict[str, Any]:
        """
        Get comprehensive subtopic analysis for a company
        """
        try:
            result = self.supabase.table("company_subtopic_analysis").select("*").eq("company_name", company_name).execute()

            if result.data:
                return result.data[0]
            else:
                return {"company_name": company_name, "topics_with_subtopics": 0, "total_subtopics": 0}

        except Exception as e:
            self.logger.error(f"Error getting subtopic analysis for {company_name}: {e}")
            return {"company_name": company_name, "error": str(e)}

    def search_subtopics_by_name(self, company_name: str, subtopic_name_pattern: str) -> List[Dict[str, Any]]:
        """
        Search for subtopics by name pattern within a company's topics
        """
        try:
            # Use PostgreSQL's JSONB operators to search within subtopic names
            result = self.supabase.rpc('search_subtopics_by_name', {
                'company_name_param': company_name,
                'name_pattern': subtopic_name_pattern
            }).execute()

            return result.data

        except Exception as e:
            self.logger.error(f"Error searching subtopics for pattern '{subtopic_name_pattern}': {e}")
            return []

    def get_subtopic_sources(self, topic_id: int, subtopic_name: str) -> Dict[str, Any]:
        """
        Get all sources and article indices for a specific subtopic
        """
        try:
            # Query the subtopic_detail view for a specific subtopic
            result = self.supabase.table("subtopic_detail").select(
                "subtopic_sources, subtopic_article_indices, subtopic_confidence, subtopic_extraction_method"
            ).eq("topic_id", topic_id).eq("subtopic_name", subtopic_name).execute()

            if result.data:
                return result.data[0]
            else:
                return {"error": "Subtopic not found"}

        except Exception as e:
            self.logger.error(f"Error getting sources for subtopic '{subtopic_name}' in topic {topic_id}: {e}")
            return {"error": str(e)}

    def get_high_confidence_subtopics(self, company_name: str, min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        Get subtopics with confidence above a threshold for a company
        """
        try:
            # Use the subtopic_detail view with confidence filtering
            result = self.supabase.table("subtopic_detail").select("*").gte("subtopic_confidence", min_confidence).execute()

            # Filter by company through the topic relationship
            company_subtopics = []
            for row in result.data:
                # Get company info for this topic
                topic_info = self.supabase.table("topics").select("companies(name)").eq("id", row["topic_id"]).execute()
                if topic_info.data and topic_info.data[0]["companies"]["name"] == company_name:
                    company_subtopics.append(row)

            return company_subtopics

        except Exception as e:
            self.logger.error(f"Error getting high-confidence subtopics for {company_name}: {e}")
            return []

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def clean_old_data(self, company_name: str, days_old: int = 30) -> None:
        """
        Clean up old research data for a company
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            # Delete old topics (will cascade to article_topics)
            result = self.supabase.table("topics").delete().eq("companies.name", company_name).lt("extraction_date", cutoff_date).execute()

            deleted_count = len(result.data) if result.data else 0
            self.logger.info(f"Cleaned up {deleted_count} old topics for {company_name}")

        except Exception as e:
            self.logger.error(f"Error cleaning old data for {company_name}: {e}")

    # ============================================================================
    # SUBTOPIC SERIALIZATION METHODS
    # ============================================================================

    def _serialize_subtopics(self, subtopics: List[Subtopic]) -> List[Dict[str, Any]]:
        """Convert Subtopic objects to JSON-serializable dictionaries"""
        if not subtopics:
            return []

        serialized = []
        for subtopic in subtopics:
            if isinstance(subtopic, str):
                # Handle backward compatibility - convert old string subtopics
                serialized.append({
                    "name": subtopic,
                    "sources": [],
                    "article_indices": [],
                    "confidence": 0.5,
                    "extraction_method": "legacy_string"
                })
            else:
                # New Subtopic object
                serialized.append({
                    "name": subtopic.name,
                    "sources": subtopic.sources,
                    "article_indices": subtopic.article_indices,
                    "confidence": subtopic.confidence,
                    "extraction_method": subtopic.extraction_method
                })
        return serialized

    def _deserialize_subtopics(self, subtopics_data: Any) -> List[Subtopic]:
        """Convert JSON data back to Subtopic objects"""
        if not subtopics_data:
            return []

        subtopics = []
        for item in subtopics_data:
            if isinstance(item, str):
                # Handle old format - string subtopics
                subtopics.append(Subtopic(
                    name=item,
                    sources=[],
                    article_indices=[],
                    confidence=0.5,
                    extraction_method="legacy_string"
                ))
            elif isinstance(item, dict):
                # New format - object subtopics
                subtopics.append(Subtopic(
                    name=item.get("name", ""),
                    sources=item.get("sources", []),
                    article_indices=item.get("article_indices", []),
                    confidence=item.get("confidence", 0.5),
                    extraction_method=item.get("extraction_method", "unknown")
                ))
        return subtopics