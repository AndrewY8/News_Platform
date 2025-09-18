import logging
import asyncio
from typing import List, Dict, Any, Optional
from .prompts import augment_query, pick_tavily_params
from .actions.retriever import get_retriever_tasks
import google.genai as genai
import json
from datetime import datetime

from .retrievers.tavily.tavily_search import TavilyRetriever
from .retrievers.EDGAR.EDGAR import EDGARRetriever

logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self, max_concurrent_retrievers: int = 5):
        """
        Initialize the Planner Agent
        
        Args:
            max_concurrent_retrievers (int): Maximum number of retrievers to run concurrently
        """
        self.max_concurrent_retrievers = max_concurrent_retrievers
        self.client = genai.Client() 
    
    async def _run_retriever_task(self, retriever, task: str) -> Optional[Dict[str, Any]]:
        """
        Run a single retriever task with error handling
        
        Args:
            retriever: The retriever instance
            task (str): The augmented query/task to execute
            
        Returns:
            Optional[Dict[str, Any]]: Results from the retriever or None if failed
        """
        try:
            retriever_name = retriever.__name__
            logger.info(f"Running {retriever_name} with task")
             
            if (retriever == TavilyRetriever):
            # get cusotm parameters for tavilly search
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash", contents=pick_tavily_params(task), config={"response_mime_type": "application/json"}
                ) 
                print("TAVILY PARAMS")
                print(response.text)
                tavily_params = response.text
                tavily_params = json.loads(tavily_params)
                tavily_params["days"] = int(tavily_params["days"])
                tavily_params["max_results"] = int(tavily_params["max_results"])
                tavily_params["include_answer"] = bool(tavily_params["include_answer"])
        
                print(tavily_params)
            
                # Run the retriever
                
                ret_obj = retriever(task);
                if asyncio.iscoroutinefunction(ret_obj.search):
                    result = await ret_obj.search(**tavily_params)
                else:
                    result = ret_obj.search(**tavily_params)
            else:
                print(f"PROCESSING {retriever_name}")
                ret_obj = retriever(task);
                if asyncio.iscoroutinefunction(ret_obj.search):
                    result = await ret_obj.search()
                else:
                    result = ret_obj.search()
                print(f"PROCESSED{result}")
                
            
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
            
            # Step 1: Augment the query 
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=augment_query(query)
            ) 
            # parse response to a list of queries
            parse_queries = lambda s: [line.split('@@@', 1)[1] for line in s.strip().split('\n') if '@@@' in line]

            augmented_queries = parse_queries(response.text)

            
            with open(f"queries{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt", "w") as f:
                for augmented_query in augmented_queries:
                    f.write(augmented_query + "\n")
        
            logger.info("Query augmented successfully")
            
            # Step 2: Get retriever tasks
            retriever_tasks = get_retriever_tasks(augmented_queries, self.client)
                
            # retriever_tasks = get_retriever_tasks(augmented_query)
            logger.info(f"Created {len(retriever_tasks)} retriever tasks")
            
            # Step 3: Run retrievers in batches
            
            # hardcode edgar call for now
            retriever_tasks.append((EDGARRetriever, query))
            all_results = await self._run_retrievers_batch(retriever_tasks)
            
            print("jk")
            print(type(all_results))
            print(all_results)
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