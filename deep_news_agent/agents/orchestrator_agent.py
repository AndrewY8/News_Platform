"""
Orchestrator Agent - Coordinates the entire company research pipeline
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio

from .interfaces import (
    OrchestratorInterface, TopicExtractorInterface, SearchInterface, RankingInterface,
    CompanyContext, Topic, Question, RankedTopic, PipelineState, SearchResult,
    PipelineEvent, PipelineEventData, PipelineConfig
)
from ..prompts import (
    BUSINESS_AREA_QUESTION_TEMPLATE,
    MARKET_QUESTION_TEMPLATE,
    RECENT_NEWS_QUESTION,
    CONTEXT_NEWS_QUESTION,
    BUSINESS_GROWTH_TEMPLATE,
    LEADERSHIP_PERSONNEL_QUESTION
)
from ..db.research_db_manager import ResearchDBManager


class OrchestratorAgent(OrchestratorInterface):
    """
    Orchestrates the complete research pipeline:
    1. Initial search (Tavily + earnings)
    2. Topic extraction and memory update
    3. Question generation for next iteration
    4. Repeat for 5 iterations
    5. Final ranking of all topics
    """

    def __init__(
        self,
        topic_agent: TopicExtractorInterface,
        search_agent: SearchInterface,
        ranking_agent: RankingInterface,
        pipeline_config: PipelineConfig,
        db_manager: Optional[ResearchDBManager] = None
    ):
        self.topic_agent = topic_agent
        self.search_agent = search_agent
        self.ranking_agent = ranking_agent
        self.config = pipeline_config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

        # Pipeline state tracking
        self.current_state: Optional[PipelineState] = None
        self.event_handlers: List = []
        self.company_id: Optional[int] = None

    async def run_pipeline(self, company_context: CompanyContext) -> List[RankedTopic]:
        """
        Run the complete research pipeline for a company

        Pipeline Flow:
        1. Generate initial questions from company context
        2. Run 5 search iterations:
           - Iteration 1: Tavily + earnings search
           - Iterations 2-5: Tavily only
           - Extract topics, update memory, generate new questions
        3. Final ranking of all discovered topics
        """
        self.logger.info(f"Starting research pipeline for {company_context.name}")

        # Initialize database if available
        if self.db_manager:
            self.company_id = self.db_manager.create_or_get_company(company_context)
            self.logger.info(f"Database integration enabled - Company ID: {self.company_id}")

        # Initialize pipeline state
        initial_questions = await self._generate_initial_questions(company_context)
        self.current_state = PipelineState(
            company_context=company_context,
            current_iteration=0,
            max_iterations=self.config.max_iterations,
            topic_memory=[],
            current_questions=initial_questions,
            all_search_results=[],
            pipeline_start_time=datetime.now()
        )

        await self._emit_event(PipelineEvent.ITERATION_STARTED, {"iteration": 0})

        try:
            # Run search iterations
            for iteration in range(1, self.config.max_iterations + 1):
                self.logger.info(f"Starting iteration {iteration}/{self.config.max_iterations}")

                self.current_state.current_iteration = iteration
                self.current_state = await self.run_single_iteration(self.current_state)

                await self._emit_event(
                    PipelineEvent.ITERATION_COMPLETED,
                    {
                        "iteration": iteration,
                        "topics_found": len(self.current_state.topic_memory),
                        "questions_generated": len(self.current_state.current_questions)
                    }
                )

            # Final ranking
            self.logger.info("Running final topic ranking")
            ranked_topics = await self.ranking_agent.rank_topics(
                self.current_state.topic_memory,
                company_context
            )

            # Store final rankings in database
            if self.db_manager and ranked_topics:
                self.db_manager.update_topic_rankings(ranked_topics)
                self.logger.info("Updated topic rankings in database")

            await self._emit_event(
                PipelineEvent.PIPELINE_COMPLETED,
                {
                    "total_topics": len(ranked_topics),
                    "total_search_results": len(self.current_state.all_search_results),
                    "duration_seconds": (datetime.now() - self.current_state.pipeline_start_time).seconds
                }
            )

            self.logger.info(f"Pipeline completed. Found {len(ranked_topics)} ranked topics")
            return ranked_topics

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            await self._emit_event(PipelineEvent.ERROR_OCCURRED, {"error": str(e)}, error=e)
            raise

    async def run_single_iteration(self, state: PipelineState) -> PipelineState:
        """
        Run a single iteration of the search-extract-generate cycle
        """
        iteration = state.current_iteration

        # Step 1: Search (initial vs subsequent)
        if iteration == 1:
            search_results = await self.search_agent.initial_search(
                state.company_context,
                state.current_questions
           )
        else:
            search_results = await self.search_agent.subsequent_search(
                state.company_context,
                state.current_questions
            )

        state.all_search_results.extend(search_results)
        await self._emit_event(
            PipelineEvent.SEARCH_COMPLETED,
            {"iteration": iteration, "results_found": len(search_results)}
        )

        new_topics = await self.topic_agent.extract_topics(
            search_results,
            state.company_context,
            iteration,
            self.company_id
        )

        await self._emit_event(
            PipelineEvent.TOPICS_EXTRACTED,
            {"iteration": iteration, "topics_extracted": len(new_topics)}
        )

        await self.topic_agent.update_memory(new_topics, state.company_context)
        state.topic_memory = self.topic_agent.get_memory_topics()
        await self._emit_event(
            PipelineEvent.MEMORY_UPDATED,
            {"iteration": iteration, "total_topics_in_memory": len(state.topic_memory)}
        )

        if iteration < state.max_iterations:
            next_questions = await self.search_agent.generate_questions_from_topics(
                [{"name": t.name, "description": t.description} for t in state.topic_memory],
                state.company_context,
                iteration + 1
            )

            state.current_questions = next_questions[:self.config.max_questions_per_iteration]

            await self._emit_event(
                PipelineEvent.QUESTIONS_GENERATED,
                {"iteration": iteration, "questions_generated": len(state.current_questions)}
            )
        else:
            state.current_questions = []

        return state

    async def _generate_initial_questions(self, company_context: CompanyContext) -> List[Question]:
        """
        Generate initial research questions based on company context
        """
        # Create basic initial questions based on business areas
        initial_questions = []

        for i, business_area in enumerate(company_context.business_areas[:5]):
            question = Question(
                text=BUSINESS_AREA_QUESTION_TEMPLATE.format(
                    business_area=business_area,
                    company_name=company_context.name
                ),
                priority=i + 1,
                iteration_number=1,
                topic_source="company_context",
                confidence=0.8
            )
            initial_questions.append(question)

        # Add general market question
        market_question = Question(
            text=MARKET_QUESTION_TEMPLATE.format(company_name=company_context.name),
            priority=len(initial_questions) + 1,
            iteration_number=1,
            topic_source="company_context",
            confidence=0.9
        )
        initial_questions.append(market_question)

        # Add recent breaking news question (high priority)
        recent_news_question = Question(
            text=RECENT_NEWS_QUESTION.format(company_name=company_context.name),
            priority=len(initial_questions) + 1,
            iteration_number=1,
            topic_source="company_context",
            confidence=0.95
        )
        initial_questions.append(recent_news_question)

        # Add geopolitical context question
        context_question = Question(
            text=CONTEXT_NEWS_QUESTION.format(company_name=company_context.name),
            priority=len(initial_questions) + 1,
            iteration_number=1,
            topic_source="company_context",
            confidence=0.7
        )
        initial_questions.append(context_question)

        # Add business growth/corporate activities question
        growth_question = Question(
            text=BUSINESS_GROWTH_TEMPLATE.format(company_name=company_context.name).strip(),
            priority=len(initial_questions) + 1,
            iteration_number=1,
            topic_source="company_context",
            confidence=0.85
        )
        initial_questions.append(growth_question)

        # Add leadership/personnel changes question
        leadership_question = Question(
            text=LEADERSHIP_PERSONNEL_QUESTION.format(company_name=company_context.name).strip(),
            priority=len(initial_questions) + 1,
            iteration_number=1,
            topic_source="company_context",
            confidence=0.8
        )
        initial_questions.append(leadership_question)

        self.logger.info(f"Generated {len(initial_questions)} initial questions")
        return initial_questions

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline execution status"""
        if not self.current_state:
            return {"status": "not_started"}

        return {
            "status": "completed" if self.current_state.is_complete() else "running",
            "company": self.current_state.company_context.name,
            "current_iteration": self.current_state.current_iteration,
            "max_iterations": self.current_state.max_iterations,
            "topics_in_memory": len(self.current_state.topic_memory),
            "current_questions": len(self.current_state.current_questions),
            "total_search_results": len(self.current_state.all_search_results),
            "elapsed_time_seconds": (
                datetime.now() - self.current_state.pipeline_start_time
            ).seconds if self.current_state.pipeline_start_time else 0
        }

    def add_event_handler(self, handler) -> None:
        """Add an event handler for pipeline monitoring"""
        self.event_handlers.append(handler)

    def remove_event_handler(self, handler) -> None:
        """Remove an event handler"""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)

    async def _emit_event(
        self,
        event: PipelineEvent,
        data: Dict[str, Any],
        error: Optional[Exception] = None
    ) -> None:
        """Emit a pipeline event to all registered handlers"""
        event_data = PipelineEventData(
            event=event,
            iteration=self.current_state.current_iteration if self.current_state else 0,
            timestamp=datetime.now(),
            data=data,
            error=error
        )

        # Log the event
        if error:
            self.logger.error(f"Pipeline event {event.value}: {data} - Error: {error}")
        else:
            self.logger.info(f"Pipeline event {event.value}: {data}")

        # Notify handlers
        for handler in self.event_handlers:
            try:
                await handler.handle_event(event_data)
            except Exception as e:
                self.logger.warning(f"Event handler failed: {e}")

    async def pause_pipeline(self) -> None:
        """Pause pipeline execution (placeholder for future implementation)"""
        self.logger.info("Pipeline pause requested")
        # TODO: Implement pause functionality

    async def resume_pipeline(self) -> None:
        """Resume pipeline execution (placeholder for future implementation)"""
        self.logger.info("Pipeline resume requested")
        # TODO: Implement resume functionality

    async def cancel_pipeline(self) -> None:
        """Cancel pipeline execution (placeholder for future implementation)"""
        self.logger.info("Pipeline cancellation requested")
        # TODO: Implement cancellation functionality