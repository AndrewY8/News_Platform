"""
Common interfaces and data models for all agents
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from enum import Enum


# ============ SHARED DATA MODELS ============

@dataclass
class Subtopic:
    """Subtopic with dedicated source tracking"""
    name: str
    sources: List[str]
    article_indices: List[int]
    confidence: float
    extraction_method: str = "llm_subtopic"

    def __post_init__(self):
        if self.article_indices is None:
            self.article_indices = []

@dataclass
class CompanyContext:
    """Company information for research context"""
    name: str
    business_areas: List[str]
    current_status: Dict[str, Any]
    ticker: Optional[str] = None
    industry: Optional[str] = None


class urgency(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


@dataclass
class Topic:
    """Extracted business topic"""
    name: str
    description: str
    business_impact: str
    confidence: float
    sources: List[str]
    subtopics: List[Subtopic]
    urgency: urgency
    extraction_date: datetime
    source_article_indices: List[int] = None  # Indices of articles that support this topic

    def __post_init__(self):
        if self.source_article_indices is None:
            self.source_article_indices = []
        if self.subtopics is None:
            self.subtopics = []

    @classmethod
    def from_model(cls, topic_model) -> 'Topic':
        """Create Topic from Pydantic model"""
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

        return cls(
            name=topic_model.name,
            description=topic_model.description,
            business_impact=topic_model.business_impact,
            confidence=topic_model.confidence,
            sources=topic_model.sources,
            subtopics=subtopic_objects,
            urgency=topic_model.urgency,
            extraction_date=datetime.now()
        )


@dataclass
class Question:
    """Research question for search"""
    text: str
    priority: int
    iteration_number: int
    topic_source: str
    confidence: float = 0.8


@dataclass
class RankedTopic:
    """Topic with ranking information"""
    topic: Topic
    final_score: float
    impact_score: float
    recency_score: float
    relatedness_score: float
    credibility_score: float
    rank: int


# ============ SEARCH RESULT ABSTRACTIONS ============

@dataclass
class SearchResult(ABC):
    """Abstract base class for search results"""
    content: str
    timestamp: datetime
    source: str

    @abstractmethod
    def get_display_title(self) -> str:
        """Get title for display purposes"""
        pass

    @abstractmethod
    def get_url(self) -> Optional[str]:
        """Get URL if available"""
        pass


@dataclass
class TavilySearchResult(SearchResult):
    """Search result from Tavily web search"""
    url: str
    title: str
    relevance_score: float

    def get_display_title(self) -> str:
        return self.title

    def get_url(self) -> Optional[str]:
        return self.url


@dataclass
class EarningsSearchResult(SearchResult):
    """Search result from earnings transcript"""
    company_name: str
    quarter: str
    fiscal_year: str
    transcript_type: str

    def get_display_title(self) -> str:
        return f"{self.company_name} {self.quarter} {self.fiscal_year} {self.transcript_type}"

    def get_url(self) -> Optional[str]:
        return None


# ============ PIPELINE STATE ============

@dataclass
class PipelineState:
    """Current state of the research pipeline"""
    company_context: CompanyContext
    current_iteration: int
    max_iterations: int
    topic_memory: List[Topic]
    current_questions: List[Question]
    all_search_results: List[SearchResult]
    pipeline_start_time: datetime

    def is_complete(self) -> bool:
        """Check if pipeline has completed all iterations"""
        return self.current_iteration >= self.max_iterations


# ============ AGENT INTERFACES ============

class TopicExtractorInterface(ABC):
    """Interface for topic extraction agents"""

    @abstractmethod
    async def extract_topics(self, search_results: List[SearchResult], company_context: CompanyContext) -> List[Topic]:
        """Extract topics from search results"""
        pass

    @abstractmethod
    async def update_memory(self, new_topics: List[Topic], company_context: CompanyContext) -> None:
        """Update topic memory with new topics"""
        pass

    @abstractmethod
    def get_memory_topics(self) -> List[Topic]:
        """Get all topics in memory"""
        pass


class SearchInterface(ABC):
    """Interface for search agents"""

    @abstractmethod
    async def initial_search(self, company_context: CompanyContext, questions: List[Question]) -> List[SearchResult]:
        """Perform initial search with all retrievers"""
        pass

    @abstractmethod
    async def subsequent_search(self, company_context: CompanyContext, questions: List[Question]) -> List[SearchResult]:
        """Perform subsequent search with limited retrievers"""
        pass

    @abstractmethod
    async def generate_questions_from_topics(self, topics: List[Topic], company_context: CompanyContext, iteration: int) -> List[Question]:
        """Generate research questions from topics"""
        pass


class RankingInterface(ABC):
    """Interface for ranking agents"""

    @abstractmethod
    async def rank_topics(self, topics: List[Topic], company_context: CompanyContext) -> List[RankedTopic]:
        """Rank topics by relevance and importance"""
        pass

    @abstractmethod
    def calculate_topic_score(self, topic: Topic, company_context: CompanyContext) -> Dict[str, float]:
        """Calculate individual scoring components"""
        pass


class OrchestratorInterface(ABC):
    """Interface for orchestrator agents"""

    @abstractmethod
    async def run_pipeline(self, company_context: CompanyContext) -> List[RankedTopic]:
        """Run the complete research pipeline"""
        pass

    @abstractmethod
    async def run_single_iteration(self, state: PipelineState) -> PipelineState:
        """Run a single iteration of the pipeline"""
        pass

    @abstractmethod
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        pass


# ============ EVENT SYSTEM ============

class PipelineEvent(Enum):
    """Events that can occur during pipeline execution"""
    ITERATION_STARTED = "iteration_started"
    SEARCH_COMPLETED = "search_completed"
    TOPICS_EXTRACTED = "topics_extracted"
    MEMORY_UPDATED = "memory_updated"
    QUESTIONS_GENERATED = "questions_generated"
    ITERATION_COMPLETED = "iteration_completed"
    PIPELINE_COMPLETED = "pipeline_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class PipelineEventData:
    """Data associated with pipeline events"""
    event: PipelineEvent
    iteration: int
    timestamp: datetime
    data: Dict[str, Any]
    error: Optional[Exception] = None


class EventHandler(ABC):
    """Interface for handling pipeline events"""

    @abstractmethod
    async def handle_event(self, event_data: PipelineEventData) -> None:
        """Handle a pipeline event"""
        pass


# ============ CONFIGURATION ============

@dataclass
class AgentConfig:
    """Configuration for individual agents"""
    openai_api_key: str
    tavily_api_key: Optional[str] = None
    max_tokens: int = 200
    temperature: float = 0.1
    max_search_results: int = 20
    confidence_threshold: float = 0.7
    rate_limit_delay: float = 1.0


@dataclass
class PipelineConfig:
    """Configuration for the entire pipeline"""
    max_iterations: int = 5
    max_questions_per_iteration: int = 8
    max_topics_in_memory: int = 50
    enable_earnings_retrieval: bool = True
    enable_fallback_strategies: bool = True
    parallel_processing: bool = False


# ============ FACTORY PATTERN ============

class AgentFactory:
    """Factory for creating agent instances"""

    @staticmethod
    def create_topic_agent(config: AgentConfig):
        """Create a topic extraction agent"""
        from .topic_agent import TopicAgent
        return TopicAgent(
            openai_api_key=config.openai_api_key,
            max_tokens=config.max_tokens
        )

    @staticmethod
    def create_search_agent(config: AgentConfig):
        """Create a search agent"""
        from .search_agent import SearchAgent
        return SearchAgent(
            tavily_api_key=config.tavily_api_key,
            openai_api_key=config.openai_api_key
        )

    @staticmethod
    def create_ranking_agent(config: AgentConfig):
        """Create a ranking agent"""
        from .ranking_agent import RankingAgent
        return RankingAgent(
            openai_api_key=config.openai_api_key,
            max_tokens=config.max_tokens
        )

    @staticmethod
    def create_orchestrator_agent(config: AgentConfig, pipeline_config: PipelineConfig):
        """Create an orchestrator agent"""
        from .orchestrator_agent import OrchestratorAgent
        return OrchestratorAgent(
            topic_agent=AgentFactory.create_topic_agent(config),
            search_agent=AgentFactory.create_search_agent(config),
            ranking_agent=AgentFactory.create_ranking_agent(config),
            pipeline_config=pipeline_config
        )