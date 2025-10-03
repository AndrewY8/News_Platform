"""
Topic Agent - Extracts and manages business-relevant topics using LLM analysis
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel

from .interfaces import (
    TopicExtractorInterface, Topic, CompanyContext, SearchResult, Subtopic,
    urgency
)
from ..prompts import TOPIC_EXTRACTION_PROMPT, TOPIC_MERGE_PROMPT, TOPIC_COMBINATION_PROMPT


# Pydantic models for structured LLM responses
class TopicModel(BaseModel):
    name: str
    description: str
    business_impact: str
    confidence: float
    sources: List[str]
    subtopics: List[str]
    urgency: urgency
    source_article_indices: List[int]  # Indices of articles that support this topic


class TopicsResponse(BaseModel):
    topics: List[TopicModel]

class actions(str, Enum):
    MERGE = "merge"
    ADD = "add"
    ADD_SUBTOPIC = "add_subtopic"
    SKIP = "skip"

class MergeAction(BaseModel):
    action: actions  # "merge", "add", "add_subtopic", or "skip"
    new_topic_index: int
    existing_topic_index: Optional[int] = None
    reason: str

class MergeResponse(BaseModel):
    actions: List[MergeAction]

class SubtopicModel(BaseModel):
    name: str
    sources: List[str]
    article_indices: List[int]
    confidence: float
    extraction_method: str = "llm_subtopic"  # How this subtopic was created

class MergedTopicModel(BaseModel):
    name: str
    description: str
    business_impact: str
    urgency: urgency
    confidence: float

# Add class methods to Subtopic for convenience
def subtopic_from_model(subtopic_model: SubtopicModel) -> Subtopic:
    return Subtopic(
        name=subtopic_model.name,
        sources=subtopic_model.sources,
        article_indices=subtopic_model.article_indices,
        confidence=subtopic_model.confidence,
        extraction_method=subtopic_model.extraction_method
    )

def subtopic_from_topic(topic: Topic) -> Subtopic:
    """Create a subtopic from a full topic (for add_subtopic action)"""
    return Subtopic(
        name=topic.name,
        sources=topic.sources.copy(),
        article_indices=topic.source_article_indices.copy() if topic.source_article_indices else [],
        confidence=topic.confidence,
        extraction_method="topic_to_subtopic"
    )

# Enhanced Topic.from_model to handle source_article_indices
def enhanced_topic_from_model(topic_model: TopicModel) -> Topic:
    # Convert string subtopics to Subtopic objects
    subtopic_objects = []
    for subtopic_name in topic_model.subtopics:
        subtopic_objects.append(Subtopic(
            name=subtopic_name,
            sources=[],  # Initially empty, will be populated when subtopics are added
            article_indices=[],
            confidence=0.5,  # Default confidence for string-converted subtopics
            extraction_method="initial_extraction"
        ))

    topic = Topic.from_model(topic_model)
    topic.subtopics = subtopic_objects
    topic.source_article_indices = topic_model.source_article_indices if hasattr(topic_model, 'source_article_indices') else []
    return topic


@dataclass
class CompanyContext:
    name: str
    business_areas: List[str]
    current_status: Dict[str, Any]


class TopicAgent:
    def __init__(self, openai_api_key: str, max_tokens: int = 200, db_manager = None):
        self.client = OpenAI(api_key=openai_api_key)
        self.max_tokens = max_tokens
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.memory_topics: List[Topic] = []

    async def extract_topics(self, search_results: List[SearchResult], company_context: CompanyContext,
                           iteration: int = 1, company_id: Optional[int] = None) -> List[Topic]:
        """Extract important business topics from search results using GPT-4"""
        try:
            prompt = self._build_extraction_prompt(search_results, company_context)

            response = self.client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "topics_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "topics": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "description": {"type": "string"},
                                            "business_impact": {"type": "string"},
                                            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                            "sources": {"type": "array", "items": {"type": "string"}},
                                            "subtopics": {"type": "array", "items": {"type": "string"}},
                                            "urgency": {"type": "string", "enum": ["high", "medium", "low"]},
                                            "source_article_indices": {"type": "array", "items": {"type": "integer", "minimum": 0}}
                                        },
                                        "required": ["name", "description", "business_impact", "confidence", "sources", "subtopics", "urgency", "source_article_indices"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["topics"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            )

            # Parse the JSON response
            import json
            topics_data = json.loads(response.output_text)
            topics_response = TopicsResponse(**topics_data)

            topics = []
            for topic_model in topics_response.topics:
                topic = enhanced_topic_from_model(topic_model)
                topics.append(topic)

            # Store topics in database if available
            if self.db_manager and topics and company_id:
                # Step 1: Store articles from search results first
                primary_query = f"Research iteration {iteration}"
                stored_articles = self.db_manager.store_search_results(search_results, primary_query, iteration)
                self.logger.info(f"Stored {len(stored_articles)} articles in database")

                # Step 2: Store topics with deterministic article relationships
                stored_topics = []
                for topic in topics:
                    # Store the topic
                    stored_topic = self.db_manager.store_single_topic(topic, company_id, iteration)
                    stored_topics.append(stored_topic)

                    # Step 3: Create article-topic relationships using indices
                    if topic.source_article_indices:
                        relationships = []
                        for article_index in topic.source_article_indices:
                            # Validate index is within bounds
                            if 0 <= article_index < len(stored_articles):
                                relationships.append({
                                    "article_id": stored_articles[article_index].id,
                                    "topic_id": stored_topic.id,
                                    "contribution_strength": 1.0,  # Full contribution since explicitly cited
                                    "extraction_method": "llm_citation"
                                })
                            else:
                                self.logger.warning(f"Invalid article index {article_index} for topic '{topic.name}' (max: {len(stored_articles)-1})")

                        # Store the relationships
                        if relationships:
                            self.db_manager.store_article_topic_relationships(relationships)
                            self.logger.debug(f"Created {len(relationships)} article-topic relationships for '{topic.name}'")

                self.logger.info(f"Stored {len(stored_topics)} topics with deterministic article citations")

            self.logger.info(f"Extracted {len(topics)} topics from {len(search_results)} search results")
            return topics

        except Exception as e:
            self.logger.error(f"Error extracting topics: {e}")
            return []

    def _build_extraction_prompt(self, search_results: List[SearchResult], company_context: CompanyContext) -> str:
        """Build the prompt for GPT-4 topic extraction"""
        formatted_results = self._format_search_results(search_results)
        current_date = datetime.now().strftime("%Y-%m-%d")

        return TOPIC_EXTRACTION_PROMPT.format(
            current_date=current_date,
            company_name=company_context.name,
            business_areas=', '.join(company_context.business_areas),
            current_status=json.dumps(company_context.current_status, indent=2),
            formatted_results=formatted_results
        )

    def _format_search_results(self, search_results: List[SearchResult]) -> str:
        """Format search results for prompt with 0-based indices for citation"""
        formatted = []
        for i, result in enumerate(search_results[:10]):  # Limit to top 10 results
            formatted.append(f"""
                                Article {i}:
                                Title: {getattr(result, 'title', result.get_display_title())}
                                URL: {getattr(result, 'url', result.get_url() or 'N/A')}
                                Content: {result.content[:500]}...
                                Source: {result.source}
                                Timestamp: {result.timestamp}
                                """)
        return "\n".join(formatted)

    async def update_memory(self, new_topics: List[Topic], company_context: CompanyContext) -> None:
        """Update topic memory with new topics, handling duplicates and relationships"""
        if not self.memory_topics:
            self.memory_topics.extend(new_topics)
            self.logger.info(f"Added {len(new_topics)} topics to empty memory")
            return

        try:
            merge_prompt = self._build_merge_prompt(self.memory_topics, new_topics, company_context)

            response = self.client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": merge_prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "merge_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "actions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "action": {"type": "string", "enum": ["merge", "add", "add_subtopic", "skip"]},
                                            "new_topic_index": {"type": "integer"},
                                            "existing_topic_index": {"type": ["integer", "null"]},
                                            "reason": {"type": "string"}
                                        },
                                        "required": ["action", "new_topic_index", "existing_topic_index", "reason"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["actions"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                temperature=0.05  # Very low temperature for consistent deduplication decisions
            )

            # Parse the JSON response
            import json
            merge_data = json.loads(response.output_text)
            merge_decisions = MergeResponse(**merge_data)

            await self._apply_memory_updates(merge_decisions, new_topics)

        except Exception as e:
            self.logger.error(f"Error updating memory: {e}")
            # Fallback: just append new topics
            self.memory_topics.extend(new_topics)

    def _build_merge_prompt(self, existing_topics: List[Topic], new_topics: List[Topic], company_context: CompanyContext) -> str:
        """Build prompt for merging topics"""
        existing_formatted = self._format_topics_for_prompt(existing_topics)
        new_formatted = self._format_topics_for_prompt(new_topics)

        return TOPIC_MERGE_PROMPT.format(
            company_name=company_context.name,
            existing_formatted=existing_formatted,
            new_formatted=new_formatted
        )

    def _format_topics_for_prompt(self, topics: List[Topic]) -> str:
        """Format topics for prompt display"""
        formatted = []
        for i, topic in enumerate(topics):
            formatted.append(f"""
            {i}: {topic.name}
            Description: {topic.description}
            Impact: {topic.business_impact}
            Confidence: {topic.confidence}
            Urgency: {topic.urgency}
            """)
        return "\n".join(formatted)

    async def _merge_topics_intelligently(self, existing_topic: Topic, new_topic: Topic) -> Topic:
        """Use LLM to intelligently merge two topics into a comprehensive combined topic"""
        try:
            prompt = TOPIC_COMBINATION_PROMPT.format(
                existing_name=existing_topic.name,
                existing_description=existing_topic.description,
                existing_impact=existing_topic.business_impact,
                existing_urgency=existing_topic.urgency,
                existing_confidence=existing_topic.confidence,
                new_name=new_topic.name,
                new_description=new_topic.description,
                new_impact=new_topic.business_impact,
                new_urgency=new_topic.urgency,
                new_confidence=new_topic.confidence
            )

            response = self.client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "merged_topic_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "business_impact": {"type": "string"},
                                "urgency": {"type": "string", "enum": ["high", "medium", "low"]},
                                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                            },
                            "required": ["name", "description", "business_impact", "urgency", "confidence"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                temperature=0.3  # Slightly higher temperature for creative merging
            )

            # Parse the JSON response
            import json
            merged_data = json.loads(response.output_text)
            merged_topic_model = MergedTopicModel(**merged_data)

            # Update the existing topic with merged information
            existing_topic.name = merged_topic_model.name
            existing_topic.description = merged_topic_model.description
            existing_topic.business_impact = merged_topic_model.business_impact
            existing_topic.urgency = merged_topic_model.urgency
            existing_topic.confidence = merged_topic_model.confidence

            self.logger.info(f"Intelligently merged topics: '{existing_topic.name}'")
            return existing_topic

        except Exception as e:
            self.logger.error(f"Error in intelligent topic merge: {e}")
            # Fallback to simple merge logic
            if new_topic.confidence > existing_topic.confidence:
                existing_topic.business_impact = new_topic.business_impact
                existing_topic.confidence = new_topic.confidence
            return existing_topic

    async def _apply_memory_updates(self, merge_decisions: MergeResponse, new_topics: List[Topic]) -> None:
        """Apply merge decisions to update memory"""
        for action in merge_decisions.actions:
            new_topic_idx = action.new_topic_index
            new_topic = new_topics[new_topic_idx]

            if action.action == "add":
                self.memory_topics.append(new_topic)
            elif action.action == "add_subtopic":
                existing_idx = action.existing_topic_index
                if existing_idx is not None and existing_idx < len(self.memory_topics):
                    existing_topic = self.memory_topics[existing_idx]

                    # Create a Subtopic object from the new topic with its dedicated sources
                    new_subtopic = subtopic_from_topic(new_topic)

                    # Check if subtopic with same name already exists
                    existing_subtopic_names = [st.name for st in existing_topic.subtopics]
                    if new_subtopic.name not in existing_subtopic_names:
                        existing_topic.subtopics.append(new_subtopic)
                    else:
                        # If subtopic exists, merge their sources
                        for existing_subtopic in existing_topic.subtopics:
                            if existing_subtopic.name == new_subtopic.name:
                                existing_subtopic.sources.extend(new_subtopic.sources)
                                existing_subtopic.sources = list(set(existing_subtopic.sources))
                                existing_subtopic.article_indices.extend(new_subtopic.article_indices)
                                existing_subtopic.article_indices = list(set(existing_subtopic.article_indices))
                                if new_subtopic.confidence > existing_subtopic.confidence:
                                    existing_subtopic.confidence = new_subtopic.confidence
                                break

                    # Also add sources to parent topic for backward compatibility
                    existing_topic.sources.extend(new_topic.sources)
                    existing_topic.sources = list(set(existing_topic.sources))

                    # Merge article indices to parent
                    if existing_topic.source_article_indices is None:
                        existing_topic.source_article_indices = []
                    if new_topic.source_article_indices:
                        existing_topic.source_article_indices.extend(new_topic.source_article_indices)
                        existing_topic.source_article_indices = list(set(existing_topic.source_article_indices))

                    # Update confidence if new subtopic has higher confidence
                    if new_topic.confidence > existing_topic.confidence:
                        existing_topic.confidence = new_topic.confidence

                    # Update urgency to highest level (high > medium > low)
                    urgency_priority = {"low": 1, "medium": 2, "high": 3}
                    if urgency_priority.get(new_topic.urgency, 1) > urgency_priority.get(existing_topic.urgency, 1):
                        existing_topic.urgency = new_topic.urgency

                    # Update extraction date to reflect the addition
                    existing_topic.extraction_date = datetime.now()

                    self.logger.info(f"Added '{new_topic.name}' as subtopic to '{existing_topic.name}' with {len(new_subtopic.sources)} dedicated sources")
            elif action.action == "merge":
                existing_idx = action.existing_topic_index
                if existing_idx is not None and existing_idx < len(self.memory_topics):
                    existing_topic = self.memory_topics[existing_idx]

                    # Intelligently merge the topics using LLM
                    merged_topic = await self._merge_topics_intelligently(existing_topic, new_topic)

                    # Merge sources and metadata
                    merged_topic.sources.extend(new_topic.sources)
                    merged_topic.sources = list(set(merged_topic.sources))  # Remove duplicates
                    merged_topic.subtopics.extend(new_topic.subtopics)
                    merged_topic.subtopics = list(set(merged_topic.subtopics))

                    # Merge article indices (handle None cases)
                    if merged_topic.source_article_indices is None:
                        merged_topic.source_article_indices = []
                    if new_topic.source_article_indices:
                        merged_topic.source_article_indices.extend(new_topic.source_article_indices)
                        merged_topic.source_article_indices = list(set(merged_topic.source_article_indices))  # Remove duplicates

                    # Update the extraction date to reflect the merge
                    merged_topic.extraction_date = datetime.now()
            # Skip action means do nothing

        self.logger.info(f"Memory updated. Total topics: {len(self.memory_topics)}")

    def get_memory_topics(self) -> List[Topic]:
        """Get all topics currently in memory"""
        return self.memory_topics.copy()

    def clear_memory(self) -> None:
        """Clear all topics from memory"""
        self.memory_topics.clear()
        self.logger.info("Topic memory cleared")

    def get_topics_by_urgency(self, urgency: str) -> List[Topic]:
        """Get topics filtered by urgency level"""
        return [topic for topic in self.memory_topics if topic.urgency == urgency]

    def get_high_confidence_topics(self, threshold: float = 0.7) -> List[Topic]:
        """Get topics above confidence threshold"""
        return [topic for topic in self.memory_topics if topic.confidence >= threshold]

    def get_topic_hierarchy_summary(self) -> str:
        """Get a formatted summary of the topic hierarchy with source tracking"""
        if not self.memory_topics:
            return "No topics in memory"

        summary = []
        for i, topic in enumerate(self.memory_topics):
            summary.append(f"{i+1}. {topic.name} (confidence: {topic.confidence:.2f}, urgency: {topic.urgency})")
            summary.append(f"   └── Topic sources: {len(topic.sources)} sources")

            if topic.subtopics:
                for subtopic in topic.subtopics:
                    summary.append(f"   └── {subtopic.name} (conf: {subtopic.confidence:.2f})")
                    summary.append(f"       └── Dedicated sources: {len(subtopic.sources)} sources")
                    if subtopic.sources:
                        # Show first few sources for each subtopic
                        source_preview = subtopic.sources[:2]
                        if len(subtopic.sources) > 2:
                            source_preview.append(f"... and {len(subtopic.sources) - 2} more")
                        summary.append(f"       └── {', '.join(source_preview)}")
            else:
                summary.append("   └── (no subtopics)")

        return "\n".join(summary)