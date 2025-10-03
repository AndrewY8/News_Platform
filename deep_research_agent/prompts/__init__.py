"""Centralized Prompts Module"""

# Search Agent Prompts
from .search_agent_prompts import (
    QUERY_GENERATION_PROMPT,
    QUESTION_GENERATION_PROMPT,
    EARNINGS_ANALYSIS_PROMPT
)

# Topic Agent Prompts
from .topic_agent_prompts import (
    TOPIC_EXTRACTION_PROMPT,
    TOPIC_MERGE_PROMPT,
    TOPIC_COMBINATION_PROMPT
)

# Ranking Agent Prompts
from .ranking_agent_prompts import (
    IMPACT_ASSESSMENT_PROMPT
)

# Orchestrator Agent Prompts
from .orchestrator_prompts import (
    RECENT_NEWS_QUESTION,
    CONTEXT_NEWS_QUESTION,
    BUSINESS_AREA_QUESTION_TEMPLATE,
    MARKET_QUESTION_TEMPLATE,
    BUSINESS_GROWTH_TEMPLATE,
    LEADERSHIP_PERSONNEL_QUESTION
)

__all__ = [
    # Search Agent
    "QUERY_GENERATION_PROMPT",
    "QUESTION_GENERATION_PROMPT",
    "EARNINGS_ANALYSIS_PROMPT",
    # Topic Agent
    "TOPIC_EXTRACTION_PROMPT",
    "TOPIC_MERGE_PROMPT",
    "TOPIC_COMBINATION_PROMPT",
    # Ranking Agent
    "IMPACT_ASSESSMENT_PROMPT",
    # Orchestrator Agent
    "RECENT_NEWS_QUESTION",
    "CONTEXT_NEWS_QUESTION",
    "BUSINESS_AREA_QUESTION_TEMPLATE",
    "MARKET_QUESTION_TEMPLATE",
    "BUSINESS_GROWTH_TEMPLATE",
    "LEADERSHIP_PERSONNEL_QUESTION"
]