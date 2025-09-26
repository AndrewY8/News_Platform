import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
from .prompts import augment_query, pick_tavily_params
from .actions.retriever import get_retriever_tasks
import google.generativeai as genai
import json
from datetime import datetime

from .retrievers.tavily.tavily_search import TavilyRetriever
from .retrievers.EDGAR.EDGAR import EDGARRetriever

logger = logging.getLogger(__name__)

def generate_step_description(action_type: str, details: Dict[str, Any]) -> str:
    """Generate a human-readable description of what the agent is doing"""
    try:
        # Use simple template-based descriptions for better reliability
        source = details.get('source', 'data sources')
        query = details.get('query', '')
        action = details.get('action', 'processing')

        if action_type == "query_analysis":
            return f"Analyzing '{query[:30]}...' for search strategies"
        elif action_type == "strategy_generation":
            count = details.get('count', 0)
            return f"Generated {count} targeted search strategies"
        elif action_type == "source_preparation":
            sources = details.get('sources', [])
            if len(sources) == 1:
                return f"Preparing {sources[0]} for search..."
            elif len(sources) <= 3:
                return f"Preparing {', '.join(sources[:2])}... for search"
            else:
                return f"Preparing {len(sources)} data sources for search..."
        elif action_type == "retriever_search":
            if 'Tavily' in source:
                return f"Searching financial news via Tavily..."
            elif 'EDGAR' in source:
                return f"Scanning SEC filings via EDGAR..."
            else:
                return f"Searching {source}..."
        elif action_type == "parameter_optimization":
            return f"Optimizing search parameters for {source}..."
        elif action_type == "executing_search":
            days = details.get('days', 30)
            max_results = details.get('max_results', 10)
            return f"Searching last {days} days, up to {max_results} results..."
        elif action_type == "sec_search":
            return f"Scanning SEC EDGAR for recent filings..."
        elif action_type == "search_completed":
            result_count = details.get('result_count', 0)
            return f"Found {result_count} articles from {source}"
        elif action_type == "search_completion":
            total_articles = details.get('total_articles', 0)
            successful_sources = details.get('successful_sources', 0)
            return f"Search complete: {total_articles} articles from {successful_sources} sources"
        elif action_type == "search_error":
            return f"Error searching {source}, trying alternatives..."
        else:
            return f"Processing {source}..."

    except Exception as e:
        logger.error(f"Error generating step description: {e}")
        # Fallback to simple description
        return f"Searching {details.get('source', 'data sources')}..."

class PlannerAgent:
    def __init__(self, max_concurrent_retrievers: int = 5):
        """
        Initialize the Planner Agent

        Args:
            max_concurrent_retrievers (int): Maximum number of retrievers to run concurrently
        """
        self.max_concurrent_retrievers = max_concurrent_retrievers
        # Configure Gemini API
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # Initialize Gemini client for retriever tasks
        self.client = genai 
    
    async def _run_retriever_task(self, retriever, task: str, progress_callback=None) -> Optional[Dict[str, Any]]:
        """
        Run a single retriever task with error handling and detailed progress

        Args:
            retriever: The retriever instance
            task (str): The augmented query/task to execute
            progress_callback: Optional callback for progress updates

        Returns:
            Optional[Dict[str, Any]]: Results from the retriever or None if failed
        """
        try:
            retriever_name = retriever.__name__
            logger.info(f"Running {retriever_name} with task")

            # Send detailed progress update for this specific retriever
            if progress_callback:
                details = {
                    "source": retriever_name,
                    "query": task[:50] + "..." if len(task) > 50 else task,
                    "action": "searching"
                }
                description = generate_step_description("retriever_search", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            if (retriever == TavilyRetriever):
                # get custom parameters for tavily search
                if progress_callback:
                    details = {
                        "source": "Tavily",
                        "action": "configuring_search_parameters",
                        "query": task[:30] + "..." if len(task) > 30 else task
                    }
                    description = generate_step_description("parameter_optimization", details)
                    await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content([pick_tavily_params(task)])
                print("TAVILY PARAMS")
                print(response.text)
                tavily_params = response.text
                # Extract JSON from markdown wrapper if present
                if tavily_params.startswith('```json'):
                    tavily_params = tavily_params.split('```json')[1].split('```')[0].strip()
                elif tavily_params.startswith('```'):
                    tavily_params = tavily_params.split('```')[1].strip()
                tavily_params = json.loads(tavily_params)
                tavily_params["days"] = int(tavily_params["days"])
                tavily_params["max_results"] = int(tavily_params["max_results"])
                tavily_params["include_answer"] = bool(tavily_params["include_answer"])

                if progress_callback:
                    details = {
                        "source": "Tavily",
                        "action": "executing_search",
                        "days": tavily_params.get("days", 30),
                        "max_results": tavily_params.get("max_results", 10)
                    }
                    description = generate_step_description("executing_search", details)
                    await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            elif retriever == EDGARRetriever:
                if progress_callback:
                    details = {
                        "source": "SEC EDGAR",
                        "action": "searching_filings",
                        "query": task[:30] + "..." if len(task) > 30 else task
                    }
                    description = generate_step_description("sec_search", details)
                    await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            print(f"PROCESSING {retriever_name}")
            ret_obj = retriever(task);
            if asyncio.iscoroutinefunction(ret_obj.search):
                result = await ret_obj.search()
            else:
                result = ret_obj.search()
            print(f"PROCESSED{result}")

            # Send completion update
            if progress_callback:
                result_count = len(result) if isinstance(result, list) else 0
                details = {
                    "source": retriever_name,
                    "action": "completed",
                    "result_count": result_count
                }
                description = generate_step_description("search_completed", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            # Ensure result is in expected format
            if result is None:
                result = []

            return {
                "retriever": retriever_name,
                "status": "success",
                "results": result
            }

        except Exception as e:
            logger.error(f"Error running {retriever.__class__.__name__}: {str(e)}")
            if progress_callback:
                details = {
                    "source": retriever.__class__.__name__,
                    "action": "error",
                    "error": str(e)[:30]
                }
                description = generate_step_description("search_error", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            return {
                "retriever": retriever.__class__.__name__,
                "status": "error",
                "error": str(e),
                "results": []
            }
    
    async def _run_retrievers_batch(self, retriever_tasks: List[tuple]) -> List[Dict[str, Any]]:
        """
        Run retrievers in batches to avoid overwhelming external APIs
        
        Args:
            retriever_tasks (List[tuple]): List of (retriever, task) tuples
            
        Returns:
            List[Dict[str, Any]]: Results from all retrievers
        """
        all_results = []
        
        # Process retrievers in batches
        for i in range(0, len(retriever_tasks), self.max_concurrent_retrievers):
            batch = retriever_tasks[i:i + self.max_concurrent_retrievers]
            batch_tasks = [
                self._run_retriever_task(retriever, task)
                for retriever, task in batch
            ]

            # Run batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle exceptions and collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch task failed: {str(result)}")
                    all_results.append({
                        "retriever": "unknown",
                        "status": "error", 
                        "error": str(result),
                        "results": []
                    })
                else:
                    all_results.append(result)
        
        return all_results

    async def _run_retrievers_batch_with_progress(self, retriever_tasks: List[tuple], progress_callback=None) -> List[Dict[str, Any]]:
        """
        Run retrievers in batches with progress updates

        Args:
            retriever_tasks (List[tuple]): List of (retriever, task) tuples
            progress_callback: Optional callback for progress updates

        Returns:
            List[Dict[str, Any]]: Results from all retrievers
        """
        import json
        all_results = []

        # Process retrievers in batches
        for i in range(0, len(retriever_tasks), self.max_concurrent_retrievers):
            batch = retriever_tasks[i:i + self.max_concurrent_retrievers]

            # Individual retrievers will now send their own detailed progress updates

            batch_tasks = [
                self._run_retriever_task(retriever, task, progress_callback)
                for retriever, task in batch
            ]

            # Run batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle exceptions and collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch task failed: {str(result)}")
                    all_results.append({
                        "retriever": "unknown",
                        "status": "error",
                        "error": str(result),
                        "results": []
                    })
                else:
                    all_results.append(result)

        return all_results

    async def run_async_with_progress(self, query: str, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Async version with progress updates

        Args:
            query (str): The user query to research
            progress_callback: Optional callback for progress updates

        Returns:
            List[Dict[str, Any]]: Results from all retrievers
        """
        import json

        try:
            logger.info(f"Starting planner agent with query: {query}")

            if progress_callback:
                details = {
                    "action": "analyzing_query",
                    "query": query[:50] + "..." if len(query) > 50 else query
                }
                description = generate_step_description("query_analysis", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content([augment_query(query)])
            parse_queries = lambda s: [line.split('@@@', 1)[1] for line in s.strip().split('\n') if '@@@' in line]
            augmented_queries = parse_queries(response.text)

            with open(f"queries{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
                for augmented_query in augmented_queries:
                    f.write(augmented_query + "\n")

            logger.info("Query augmented successfully")

            if progress_callback:
                # Show the actual search strategies that were generated
                sample_queries = augmented_queries[:2] if len(augmented_queries) >= 2 else augmented_queries
                details = {
                    "action": "strategies_generated",
                    "count": len(augmented_queries),
                    "sample_queries": sample_queries
                }
                description = generate_step_description("strategy_generation", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            # Step 2: Get retriever tasks
            retriever_tasks = get_retriever_tasks(augmented_queries, self.client)
            logger.info(f"Created {len(retriever_tasks)} retriever tasks")

            # Step 3: Run retrievers in batches
            retriever_tasks.append((EDGARRetriever, query))

            if progress_callback:
                # Show which data sources we're about to search
                all_retrievers = [task[0].__name__ for task in retriever_tasks]
                details = {
                    "action": "preparing_sources",
                    "sources": all_retrievers[:3],
                    "total_sources": len(all_retrievers)
                }
                description = generate_step_description("source_preparation", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            all_results = await self._run_retrievers_batch_with_progress(retriever_tasks, progress_callback)

            if progress_callback:
                successful_results = [r for r in all_results if r.get('status') == 'success']
                total_articles = sum(len(r.get('results', [])) for r in successful_results)
                details = {
                    "action": "search_completed",
                    "successful_sources": len(successful_results),
                    "total_sources": len(all_results),
                    "total_articles": total_articles
                }
                description = generate_step_description("search_completion", details)
                await progress_callback(f"data: {json.dumps({'type': 'thinking', 'step': description})}\n\n")

            return all_results

        except Exception as e:
            logger.error(f"Planner agent failed: {str(e)}")
            return []

    async def run_async(self, query: str) -> List[Dict[str, Any]]:
        """
        Async version of the main run method

        Args:
            query (str): The user query to research

        Returns:
            Dict[str, Any]: Organized results from all retrievers
        """
        try:
            logger.info(f"Starting planner agent with query: {query}")

            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content([augment_query(query)])
            parse_queries = lambda s: [line.split('@@@', 1)[1] for line in s.strip().split('\n') if '@@@' in line]
            augmented_queries = parse_queries(response.text)

            with open(f"queries{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
                for augmented_query in augmented_queries:
                    f.write(augmented_query + "\n")

            logger.info("Query augmented successfully")

            # Step 2: Get retriever tasks
            retriever_tasks = get_retriever_tasks(augmented_queries, self.client)
            logger.info(f"Created {len(retriever_tasks)} retriever tasks")

            # Step 3: Run retrievers in batches
            retriever_tasks.append((EDGARRetriever, query))
            all_results = await self._run_retrievers_batch(retriever_tasks)

            return all_results

        except Exception as e:
            logger.error(f"Planner agent failed: {str(e)}")
            return {
                "breaking_news": [],
                "financial_news": [],
                "sec_filings": [],
                "general_news": [],
                "errors": [{"retriever": "planner_agent", "error": str(e)}],
                "retriever_summary": {
                    "total_retrievers": 0,
                    "successful_retrievers": 0,
                    "failed_retrievers": 0,
                    "total_articles": 0
                }
            }
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for the async run method
        
        Args:
            query (str): The user query to research
            
        Returns:
            Dict[str, Any]: Organized results from all retrievers
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.run_async(query))
                    return future.result()
            else:
                return loop.run_until_complete(self.run_async(query))
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(self.run_async(query))