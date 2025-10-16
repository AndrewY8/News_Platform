"""
Search Agent - Handles web searches using Tavily and earnings transcript retrieval
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel

# Import the specialized retrievers
from ..retrievers.tavily.general_retriever import GeneralRetriever
from ..retrievers.tavily.trusted_news_retriever import TrustedNewsRetriever
import re
# Import the actual TavilyRetriever and transcript
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrievers.EDGAR_retriever import EDGARRetriever

# Import unified interfaces
from .interfaces import ResearchContext, CompanyContext, Question as InterfaceQuestion


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
    transcript_type: str  # "earnings_call", "guidance", etc.

    def get_display_title(self) -> str:
        return f"{self.company_name} {self.quarter} {self.fiscal_year} {self.transcript_type}"

    def get_url(self) -> Optional[str]:
        return None  # Earnings transcripts may not have URLs


# Use Question from interfaces (imported as InterfaceQuestion to avoid conflicts)
Question = InterfaceQuestion


class SearchQueryModel(BaseModel):
    query: str
    reasoning: str
    expected_info: str


class SearchQueriesResponse(BaseModel):
    queries: List[SearchQueryModel]


class SearchAgent:
    def __init__(self, tavily_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key
        self.openai_api_key = openai_api_key
        self.logger = logging.getLogger(__name__)

        # Initialize retrievers
        self.earnings_client = EDGARRetriever()

        if openai_api_key:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=openai_api_key)

    async def initial_search(self, context: ResearchContext, questions: List[Question]) -> List[SearchResult]:
        """
        Perform initial search using Tavily and (optionally) earnings transcript retrievers
        This is used for iteration 1 of the search process

        For companies: Uses both Tavily + earnings
        For macro/political: Uses only Tavily (no earnings)
        """
        self.logger.info(f"Starting initial search for {context.get_display_name()} with {len(questions)} questions")

        # Generate search queries from questions
        search_queries = await self.generate_search_queries(questions, context)

        # Search using Tavily retriever
        tavily_results = await self.search_with_tavily(search_queries, context)

        # Search using earnings transcript retriever ONLY if context supports it
        earnings_results = []
        if context.should_use_earnings():
            self.logger.info("Searching earnings transcripts (company research)")
            earnings_results = await self.search_earnings_transcripts(context)
        else:
            self.logger.info("Skipping earnings transcripts (macro/political research)")

        # Filter and rank only Tavily results (earnings always pass through)
        filtered_tavily_results = self.filter_and_rank_results(tavily_results, context)

        # Combine filtered Tavily results with earnings results (if any)
        all_results = filtered_tavily_results + earnings_results

        self.logger.info(f"Initial search completed. Found {len(filtered_tavily_results)} Tavily + {len(earnings_results)} earnings results")
        return all_results

    async def subsequent_search(self, context: ResearchContext, questions: List[Question]) -> List[SearchResult]:
        """
        Perform subsequent search using only Tavily retriever (same for both company and macro)
        This is used for iterations 2-5 of the search process
        """
        self.logger.info(f"Starting subsequent search for {context.get_display_name()} with {len(questions)} questions")

        # Generate search queries from questions
        search_queries = await self.generate_search_queries(questions, context)

        # Search using only Tavily retriever
        tavily_results = await self.search_with_tavily(search_queries, context)

        # Filter and rank results
        filtered_results = self.filter_and_rank_results(tavily_results, context)

        self.logger.info(f"Subsequent search completed. Found {len(filtered_results)} relevant results")
        return filtered_results

    async def generate_search_queries(self, questions: List[Question], context: ResearchContext) -> List[str]:
        """Generate effective search queries from questions using LLM"""
        try:
            prompt = self._build_query_generation_prompt(questions, context)

            response = self.llm_client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "search_queries_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "queries": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "query": {"type": "string"},
                                            "reasoning": {"type": "string"},
                                            "expected_info": {"type": "string"}
                                        },
                                        "required": ["query", "reasoning", "expected_info"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["queries"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                max_output_tokens=800  # Increased to accommodate 10-12 analytical queries
            )

            # Parse the structured JSON response
            import json
            text_content = response.output[0].content[0].text
            queries_response = json.loads(text_content)

            search_queries = [q["query"] for q in queries_response["queries"]]

            # Validate and truncate queries to ensure they're under 400 characters
            validated_queries = []
            for query in search_queries:
                if len(query) > 400:
                    truncated_query = query[:397] + "..."
                    self.logger.warning(f"Query truncated from {len(query)} to 400 chars: {query[:50]}...")
                    validated_queries.append(truncated_query)
                else:
                    validated_queries.append(query)

            self.logger.info(f"Generated {len(validated_queries)} search queries from {len(questions)} questions")
            return validated_queries

        except Exception as e:
            self.logger.error(f"Error generating search queries: {e}")
            # Fallback: use questions directly as queries, but truncate if needed
            fallback_queries = []
            for q in questions[:5]:  # Limit to top 5
                query_text = q.text
                if len(query_text) > 400:
                    query_text = query_text[:397] + "..."
                fallback_queries.append(query_text)
            return fallback_queries

    async def search_with_tavily(self, queries: List[str], context: ResearchContext) -> List[TavilySearchResult]:
        """Search using both General and Trusted News retrievers"""
        results = []

        for query in queries:
            try:
                self.logger.info(f"Searching with both retrievers for: {query}")

                # Check if API key is available
                import os
                if not os.environ.get('TAVILY_API_KEY'):
                    self.logger.error("TAVILY_API_KEY environment variable is not set")
                    continue

                # Search with Trusted News Retriever
                trusted_news_retriever = TrustedNewsRetriever(
                    query=query,
                    topic="general"
                )
                trusted_news_response = trusted_news_retriever.search(
                    search_depth="advanced",
                    max_results=5,  # Limit trusted news results
                    days=30
                )

                # Search with General Retriever (excludes trusted news domains)
                general_retriever = GeneralRetriever(
                    query=query,
                    topic="general"
                )
                general_response = general_retriever.search(
                    search_depth="advanced",
                    max_results=5,  # More general results to diversify sources
                    days=30
                )

                # Combine both responses
                combined_response = trusted_news_response + general_response

                # Convert response to TavilySearchResult objects
                for item in combined_response:
                    # Parse timestamp if available
                    timestamp = datetime.now()  # Default to now
                    if item.get("published_date"):
                        try:
                            timestamp = datetime.fromisoformat(item["published_date"].replace('Z', '+00:00'))
                        except:
                            pass  # Use default timestamp

                    # Use retriever_type to determine source label
                    source_label = f"tavily_{item.get('retriever_type', 'unknown')}"

                    result = TavilySearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        timestamp=timestamp,
                        source=source_label,
                        relevance_score=item.get("score", 0.5)
                    )
                    results.append(result)

                self.logger.info(f"Found {len(trusted_news_response)} trusted news + {len(general_response)} general results for query: {query}")

            except Exception as e:
                self.logger.error(f"Error searching with retrievers for query '{query}': {e}")
                continue

        return results

    async def search_earnings_transcripts(self, context: ResearchContext) -> List[EarningsSearchResult]:
        """Search earnings transcripts for the company"""
        try:
            # Get company name from context
            company_name = context.get_display_name()

            # TODO: Replace with actual earnings transcript API call
            # Example pseudo code:
            # earnings_response = self.earnings_client.get_latest_transcripts(
            #     company_name=company_name,
            #     limit=3
            # )

            self.logger.info(f"[PSEUDO] Searching earnings transcripts for: {company_name}")

            # Mock results - replace with actual API response parsing
            mock_result = EarningsSearchResult(
                company_name=company_name,
                quarter="Q3",
                fiscal_year=str(datetime.now().year),
                transcript_type="earnings_call",
                content=f"Mock earnings transcript content for {company_name}",
                timestamp=datetime.now(),
                source="earnings_transcript"
            )
            self.logger.info(f"Processing earnings transcript for: {company_name}")
            self.earnings_client.setQuery(company_name)

            # Use LLM to extract key information from the Apple earnings transcript
            if company_name.lower() in ["apple", "apple inc"]:
                # Process transcript in batches to avoid token limits
                extracted_contents = await self._process_transcript_in_batches(self.earnings_client.transcript(), self.earnings_client.systemPrompt())

                # Create earnings search result with combined extracted content
                earnings_result = EarningsSearchResult(
                    company_name="Apple Inc",
                    quarter="Q2",
                    fiscal_year="2025",
                    transcript_type="earnings_call",
                    content=extracted_contents,
                    timestamp=datetime.now(),
                    source="earnings_transcript"
                )

            # TODO: Parse actual earnings response into EarningsSearchResult objects
            # results = []
            # for transcript in earnings_response.transcripts:
            #     result = EarningsSearchResult(
            #         company_name=context.get_display_name(),
            #         quarter=transcript.quarter,
            #         fiscal_year=transcript.fiscal_year,
            #         transcript_type=transcript.type,
            #         content=transcript.content,
            #         timestamp=datetime.fromisoformat(transcript.date),
            #         source="earnings_transcript"
            #     )
            #     results.append(result)

            return [mock_result]

        except Exception as e:
            self.logger.error(f"Error searching earnings transcripts for {context.get_display_name()}: {e}")
            return []

    def filter_and_rank_results(self, results: List[TavilySearchResult], context: ResearchContext) -> List[TavilySearchResult]:
        """Filter and rank Tavily search results by relevance and quality"""
        if not results:
            return []

        # Filter out low-quality results
        filtered = [r for r in results if r.relevance_score >= 0.3]

        # Sort by relevance score (descending)
        ranked = sorted(filtered, key=lambda x: x.relevance_score, reverse=True)

        # Limit to top 20 results
        top_results = ranked[:20]

        self.logger.info(f"Filtered {len(results)} Tavily results down to {len(top_results)} high-quality results")
        return top_results

    def _build_query_generation_prompt(self, questions: List[Question], context: ResearchContext) -> str:
        """Build prompt for generating analytical search queries from questions"""
        questions_text = "\n".join([f"- {q.text}" for q in questions])

        # Get current date and year
        current_year = datetime.now().year
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Build context-specific information
        context_name = context.get_display_name()
        focus_areas = ', '.join(context.get_focus_areas())
        research_type = context.get_research_type()

        # Import analytical prompts
        from ..prompts import (
            ANALYTICAL_REASONING_FRAMEWORK,
            CREATIVE_QUERY_GENERATION_PROMPT_COMPANY,
            CREATIVE_QUERY_GENERATION_PROMPT_MACRO
        )

        # Build topics summary from memory (if available)
        topics_summary = "No topics discovered yet (first iteration)"
        if hasattr(self, '_topic_memory') and self._topic_memory:
            topics_summary = "\n".join([
                f"• {t.name}: {t.description[:120]}{'...' if len(t.description) > 120 else ''}"
                for t in self._topic_memory[:8]  # Show up to 8 topics for context
            ])

        # Build previous insights summary from questions
        previous_insights = "\n".join([
            f"• {q.text[:100]}{'...' if len(q.text) > 100 else ''}"
            for q in questions[:5]  # Show up to 5 previous questions
        ])

        # Inject analytical framework with target name
        analytical_framework = ANALYTICAL_REASONING_FRAMEWORK.format(target=context_name)

        # Use different prompts for company vs macro research
        if research_type.value == "company":
            return CREATIVE_QUERY_GENERATION_PROMPT_COMPANY.format(
                current_date=current_date,
                current_year=current_year,
                company_name=context_name,
                business_areas=focus_areas,
                analytical_framework=analytical_framework,
                topics_summary=topics_summary,
                previous_insights=previous_insights
            )
        else:  # macro or political research
            return CREATIVE_QUERY_GENERATION_PROMPT_MACRO.format(
                current_date=current_date,
                current_year=current_year,
                category_name=context_name,
                focus_areas=focus_areas,
                analytical_framework=analytical_framework,
                topics_summary=topics_summary,
                previous_insights=previous_insights
            )

    async def generate_questions_from_topics(self, topics: List[Dict], context: ResearchContext, iteration: int) -> List[Question]:
        """Generate research questions from extracted topics"""
        try:
            prompt = self._build_question_generation_prompt(topics, context, iteration)

            response = self.llm_client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "question_generation_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "questions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"},
                                            "priority": {"type": "integer"},
                                            "topic_source": {"type": "string"},
                                            "reasoning": {"type": "string"},
                                            "expected_sources": {"type": "string"}
                                        },
                                        "required": ["text", "priority", "topic_source", "reasoning", "expected_sources"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["questions"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                max_output_tokens=1500
            )

            # Parse the structured JSON response
            import json
            text_content = response.output[0].content[0].text
            questions_response = json.loads(text_content)

            questions = []

            for q_data in questions_response["questions"]:
                question = Question(
                    text=q_data["text"],
                    priority=q_data["priority"],
                    iteration_number=iteration,
                    topic_source=q_data["topic_source"]
                )
                questions.append(question)

            self.logger.info(f"Generated {len(questions)} LLM-generated questions for iteration {iteration}")
            return questions

        except Exception as e:
            self.logger.error(f"Error generating questions from topics: {e}")
            # Fallback: create basic questions from topic names
            questions = []
            for i, topic in enumerate(topics[:5]):
                question = Question(
                    text=f"What recent developments in {topic.get('name', 'topic')} could impact {context.get_display_name()}?",
                    priority=i + 1,
                    iteration_number=iteration,
                    topic_source=topic.get('name', 'unknown')
                )
                questions.append(question)
            return questions

    def _build_question_generation_prompt(self, topics: List[Dict], context: ResearchContext, iteration: int) -> str:
        """Build prompt for generating research questions from topics"""
        topics_text = "\n".join([
            f"- {topic.get('name', '')}: {topic.get('description', '')}\n  Business Impact: {topic.get('business_impact', 'Unknown')}\n  Sources Found: {', '.join(topic.get('sources', ['No sources'])[:3])}"
            for topic in topics
        ])

        # Get current year
        current_year = datetime.now().year

        # Build context-specific prompt
        context_name = context.get_display_name()
        focus_areas = ', '.join(context.get_focus_areas())

        return f"""Research Target: {context_name}
Focus Areas: {focus_areas}
Search Iteration: {iteration}

PREVIOUSLY DISCOVERED TOPICS (from iteration {iteration-1}):
{topics_text}

You are generating research questions for iteration {iteration} that will be converted into web search queries. These questions must identify specific information gaps and target new sources that weren't covered in previous searches.

**CRITICAL REQUIREMENTS:**

1. **Gap Analysis Focus:** For each topic, identify what specific information is still missing or needs deeper investigation. Don't ask broad questions about topics we already have good coverage on.

2. **Source-Aware Questions:** Design questions that would lead to different types of sources than what we already found (if sources are SEC filings, target industry reports; if sources are news articles, target analyst research, etc.)

3. **Search Query Optimization:** Frame questions using language that will generate highly targeted web search queries. Include specific:
   - Industry terminology and keywords
   - Timeframes ("{current_year}", "{current_year + 1} outlook", "recent months")
   - Source types ("analyst reports", "regulatory filings", "industry research")
   - Specific business metrics or impacts

4. **Financial Materiality:** Focus on information gaps that could significantly impact investment decisions, competitive positioning, or business performance.

5. **Avoid Redundancy:** Don't generate questions that would likely return the same sources or information we already have.

**QUESTION CATEGORIES TO PRIORITIZE:**
- Quantitative data and financial metrics not yet captured
- Forward-looking guidance, projections, or strategic plans
- Competitive intelligence and market positioning details
- Regulatory developments with specific business implications
- Operational details (capacity, expansion, efficiency metrics)
- Management commentary and strategic direction updates
- Industry expert analysis and third-party assessments

Generate 5-7 precise, search-optimized questions that target new information sources and fill specific knowledge gaps about {context.get_display_name()}."""