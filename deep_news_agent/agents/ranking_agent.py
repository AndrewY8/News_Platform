"""
Ranking Agent - Ranks topics by business relevance and impact
"""
import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel

from .interfaces import (
    RankingInterface, Topic, CompanyContext, RankedTopic
)
from ..prompts import IMPACT_ASSESSMENT_PROMPT


class ImpactAssessment(BaseModel):
    """LLM assessment of topic impact"""
    financial_impact: float  # 0-1 scale
    operational_impact: float  # 0-1 scale
    strategic_impact: float  # 0-1 scale
    urgency_factor: float  # 0-1 scale
    reasoning: str


class ImpactAssessmentResponse(BaseModel):
    """Response containing impact assessments for multiple topics"""
    assessments: List[ImpactAssessment]


class RankingAgent(RankingInterface):
    """
    Ranks topics using weighted scoring based on:
    - Impact (40%): Financial, operational, strategic impact
    - Recency (30%): How recent the information is
    - Relatedness (20%): Similarity to company's core business
    - Credibility (10%): Source trustworthiness
    """

    def __init__(self, openai_api_key: str, max_tokens: int = 400):
        self.client = OpenAI(api_key=openai_api_key)
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)

        # Scoring weights
        self.IMPACT_WEIGHT = 0.4
        self.RECENCY_WEIGHT = 0.3
        self.RELATEDNESS_WEIGHT = 0.2
        self.CREDIBILITY_WEIGHT = 0.1

        # Source credibility mapping
        self.source_credibility = {
            "sec.gov": 1.0,
            "bloomberg.com": 0.95,
            "reuters.com": 0.95,
            "wsj.com": 0.9,
            "ft.com": 0.9,
            "earnings_transcript": 0.95,
            "trusted_news": 0.9,  # High credibility for trusted news sources
            "general": 0.6,       # Lower credibility for general sources
            "tavily": 0.7,        # Legacy default for Tavily results
            "unknown": 0.5
        }

    async def rank_topics(self, topics: List[Topic], company_context: CompanyContext) -> List[RankedTopic]:
        """
        Rank topics by business relevance and return sorted list
        """
        if not topics:
            return []

        self.logger.info(f"Ranking {len(topics)} topics for {company_context.get_display_name()}")

        ranked_topics = []

        # Calculate scores for each topic
        for topic in topics:
            scores = await self.calculate_topic_score(topic, company_context)

            # Calculate final weighted score
            final_score = (
                scores["impact_score"] * self.IMPACT_WEIGHT +
                scores["recency_score"] * self.RECENCY_WEIGHT +
                scores["relatedness_score"] * self.RELATEDNESS_WEIGHT +
                scores["credibility_score"] * self.CREDIBILITY_WEIGHT
            )

            ranked_topic = RankedTopic(
                topic=topic,
                final_score=final_score,
                impact_score=scores["impact_score"],
                recency_score=scores["recency_score"],
                relatedness_score=scores["relatedness_score"],
                credibility_score=scores["credibility_score"],
                rank=0  # Will be set after sorting
            )

            ranked_topics.append(ranked_topic)

        # Sort by final score (descending)
        ranked_topics.sort(key=lambda x: x.final_score, reverse=True)

        # Assign ranks
        for i, ranked_topic in enumerate(ranked_topics):
            ranked_topic.rank = i + 1

        self.logger.info(f"Ranking completed. Top topic: {ranked_topics[0].topic.name if ranked_topics else 'None'}")
        return ranked_topics

    async def calculate_topic_score(self, topic: Topic, company_context: CompanyContext) -> Dict[str, float]:
        """
        Calculate individual scoring components for a topic
        """
        scores = {}

        # 1. Impact Score (using LLM)
        scores["impact_score"] = await self._calculate_impact_score(topic, company_context)

        # 2. Recency Score (exponential decay)
        scores["recency_score"] = self._calculate_recency_score(topic)

        # 3. Relatedness Score (business area similarity)
        scores["relatedness_score"] = self._calculate_relatedness_score(topic, company_context)

        # 4. Source Credibility Score
        scores["credibility_score"] = self._calculate_credibility_score(topic)

        return scores

    async def _calculate_impact_score(self, topic: Topic, company_context: CompanyContext) -> float:
        """
        Use LLM to assess business impact of the topic
        """
        try:
            prompt = self._build_impact_assessment_prompt(topic, company_context)

            response = self.client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "impact_assessment_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "assessments": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "financial_impact": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                            "operational_impact": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                            "strategic_impact": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                            "urgency_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                            "reasoning": {"type": "string"}
                                        },
                                        "required": ["financial_impact", "operational_impact", "strategic_impact", "urgency_factor", "reasoning"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["assessments"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            )

            # Parse the JSON response
            import json
            assessment_data = json.loads(response.output_text)
            assessment_response = ImpactAssessmentResponse(**assessment_data)
            assessment = assessment_response.assessments[0]

            # Calculate weighted impact score
            impact_score = (
                assessment.financial_impact * 0.4 +
                assessment.operational_impact * 0.3 +
                assessment.strategic_impact * 0.2 +
                assessment.urgency_factor * 0.1
            )

            return min(max(impact_score, 0.0), 1.0)  # Clamp to [0,1]

        except Exception as e:
            self.logger.warning(f"Error calculating impact score for {topic.name}: {e}")
            # Fallback: use topic confidence as proxy
            return topic.confidence

    def _calculate_recency_score(self, topic: Topic) -> float:
        """
        Calculate recency score using exponential decay (90-day half-life)
        """
        days_old = (datetime.now() - topic.extraction_date).days

        # Exponential decay with 90-day half-life
        half_life_days = 90
        recency_score = math.exp(-days_old * math.log(2) / half_life_days)

        return min(recency_score, 1.0)

    def _calculate_relatedness_score(self, topic: Topic, company_context: CompanyContext) -> float:
        """
        Calculate how related the topic is to company's business areas
        Simple keyword matching (can be enhanced with embeddings)
        """
        subtopic_names = [st.name for st in topic.subtopics] if topic.subtopics else []
        topic_text = f"{topic.name} {topic.description} {' '.join(subtopic_names)}".lower()
        business_areas_text = ' '.join(company_context.get_focus_areas()).lower()

        # Simple keyword overlap scoring
        topic_words = set(topic_text.split())
        business_words = set(business_areas_text.split())

        if not topic_words or not business_words:
            return 0.5  # Default moderate relevance

        # Calculate Jaccard similarity
        intersection = len(topic_words.intersection(business_words))
        union = len(topic_words.union(business_words))

        if union == 0:
            return 0.5

        jaccard_score = intersection / union

        # Scale and boost the score
        relatedness_score = min(jaccard_score * 2.0, 1.0)

        # Boost for high-confidence topics
        confidence_boost = topic.confidence * 0.3
        final_score = min(relatedness_score + confidence_boost, 1.0)

        return final_score

    def _calculate_credibility_score(self, topic: Topic) -> float:
        """
        Calculate source credibility score based on source domains
        """
        if not topic.sources:
            return 0.5  # Default for topics without sources

        credibility_scores = []

        for source in topic.sources:
            # Extract domain from URL or use source identifier
            if "://" in source:
                try:
                    domain = source.split("://")[1].split("/")[0]
                    # Remove www. prefix
                    if domain.startswith("www."):
                        domain = domain[4:]
                except:
                    domain = "unknown"
            else:
                domain = source

            # Get credibility score for this domain
            score = self.source_credibility.get(domain, self.source_credibility.get("unknown", 0.5))
            credibility_scores.append(score)

        # Return average credibility across all sources
        return sum(credibility_scores) / len(credibility_scores)

    def _build_impact_assessment_prompt(self, topic: Topic, company_context: CompanyContext) -> str:
        """
        Build prompt for LLM impact assessment
        """
        current_date = datetime.now().strftime("%Y-%m-%d")

        return IMPACT_ASSESSMENT_PROMPT.format(
            current_date=current_date,
            company_name=company_context.get_display_name(),
            business_areas=', '.join(company_context.get_focus_areas()),
            current_status=getattr(company_context, 'current_status', 'N/A'),
            topic_name=topic.name,
            topic_description=topic.description,
            topic_business_impact=topic.business_impact,
            topic_urgency=topic.urgency,
            topic_confidence=topic.confidence
        )

    def get_top_topics_by_category(self, ranked_topics: List[RankedTopic], category: str, limit: int = 5) -> List[RankedTopic]:
        """
        Get top topics filtered by urgency category
        """
        filtered = [rt for rt in ranked_topics if rt.topic.urgency == category]
        return filtered[:limit]

    def get_topics_above_threshold(self, ranked_topics: List[RankedTopic], threshold: float = 0.7) -> List[RankedTopic]:
        """
        Get topics above a certain final score threshold
        """
        return [rt for rt in ranked_topics if rt.final_score >= threshold]

    def generate_ranking_summary(self, ranked_topics: List[RankedTopic]) -> Dict[str, Any]:
        """
        Generate a summary of the ranking results
        """
        if not ranked_topics:
            return {"total_topics": 0}

        urgency_counts = {}
        for rt in ranked_topics:
            urgency = rt.topic.urgency
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1

        return {
            "total_topics": len(ranked_topics),
            "urgency_distribution": urgency_counts,
            "average_final_score": sum(rt.final_score for rt in ranked_topics) / len(ranked_topics),
            "top_topic": {
                "name": ranked_topics[0].topic.name,
                "score": ranked_topics[0].final_score
            } if ranked_topics else None,
            "high_impact_topics": len([rt for rt in ranked_topics if rt.impact_score >= 0.8]),
            "recent_topics": len([rt for rt in ranked_topics if rt.recency_score >= 0.8])
        }