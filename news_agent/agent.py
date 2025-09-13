import logging
import asyncio
from typing import List, Dict, Any, Optional
from .prompts import augment_query, pick_tavily_params
from .actions.retriever import get_retriever_tasks
from google import genai
import json
from datetime import datetime

try:
    from .scraper.scraper import scrape_results
except ImportError:
    scrape_results = lambda results: results  # fallback if not implemented

logger = logging.getLogger(__name__)

def extract_clean_query(augmented_query: str) -> str:
    """
    Extract the original query from the augmented prompt.
    
    Args:
        augmented_query (str): The full augmented query with instructions
        
    Returns:
        str: Clean, simple query suitable for API calls
    """
    # Look for the original query in quotes
    import re
    
    # Try to find query in quotes after "RESEARCH QUERY:" or similar patterns
    patterns = [
        r'RESEARCH QUERY:\s*"([^"]+)"',
        r'SEC FILING SEARCH:\s*"([^"]+)"', 
        r'BREAKING NEWS SEARCH:\s*"([^"]+)"',
        r'MULTI-SOURCE VERIFICATION:\s*"([^"]+)"',
        r'"([^"]+)"'  # Fallback: first quoted string
    ]
    
    for pattern in patterns:
        match = re.search(pattern, augmented_query)
        if match:
            return match.group(1).strip()
    
    # If no quotes found, try to extract first meaningful line
    lines = augmented_query.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith(('RESEARCH', 'PRIORITY', 'TARGET', 'SEARCH', 'REQUIRED', 'OUTPUT', 'TIME', '-')):
            # Remove common prefixes
            line = re.sub(r'^(QUERY:|Query:)', '', line, flags=re.IGNORECASE).strip()
            if line:
                return line
    
    # Last resort: return first 100 chars, cleaned up
    clean = re.sub(r'[^\w\s]', ' ', augmented_query[:100]).strip()
    return ' '.join(clean.split())  # Normalize whitespace

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
            retriever_name = retriever.__class__.__name__
            logger.info(f"Running {retriever_name} with task")
            
            # Check if retriever has the retrieve method
            # if not hasattr(retriever, "retrieve"):
            #     logger.warning(f"{retriever_name} does not have a retrieve method")
            #     return {
            #         "retriever": retriever_name,
            #         "status": "error",
            #         "error": "No retrieve method available",
            #         "results": []
            #     }
            
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
    
    def _filter_and_organize_results(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Filter and organize results by type (news, SEC filings, etc.)
        
        Args:
            all_results (List[Dict[str, Any]]): Raw results from all retrievers
            
        Returns:
            Dict[str, Any]: Organized results by category
        """
        organized_results = {
            "breaking_news": [],
            "financial_news": [],
            "sec_filings": [],
            "general_news": [],
            "errors": [],
            "retriever_summary": {}
        }
        
        successful_retrievers = 0
        failed_retrievers = 0
        
        for retriever_result in all_results:
            retriever_name = retriever_result.get("retriever", "unknown")
            status = retriever_result.get("status", "unknown")
            
            if status == "error":
                failed_retrievers += 1
                organized_results["errors"].append({
                    "retriever": retriever_name,
                    "error": retriever_result.get("error", "Unknown error")
                })
                continue
            
            successful_retrievers += 1
            results = retriever_result.get("results", [])
            
            # Categorize results based on content
            for item in results:
                if isinstance(item, dict):
                    # Add retriever source to each item
                    item["source_retriever"] = retriever_name
                    
                    # Categorize based on keywords and content
                    title = item.get("title", "").lower()
                    description = item.get("description", "").lower() 
                    url = item.get("url", "").lower()
                    
                    # SEC filings detection
                    if any(keyword in url for keyword in ["sec.gov", "sec", "edgar", "10-k", "10-q", "8-k", "proxy"]):
                        organized_results["sec_filings"].append(item)
                    # Breaking news detection  
                    elif any(keyword in title or keyword in description for keyword in 
                           ["breaking", "urgent", "developing", "just in", "live", "alert"]):
                        organized_results["breaking_news"].append(item)
                    # Financial news detection
                    elif any(keyword in title or keyword in description for keyword in 
                           ["earnings", "financial", "revenue", "profit", "stock", "market", "trading", "quarterly", "annual"]):
                        organized_results["financial_news"].append(item)
                    else:
                        organized_results["general_news"].append(item)
        
        # Add summary
        organized_results["retriever_summary"] = {
            "total_retrievers": len(all_results),
            "successful_retrievers": successful_retrievers,
            "failed_retrievers": failed_retrievers,
            "total_articles": sum([
                len(organized_results["breaking_news"]),
                len(organized_results["financial_news"]), 
                len(organized_results["sec_filings"]),
                len(organized_results["general_news"])
            ])
        }
        
        return organized_results
    
    async def run_async(self, query: str) -> Dict[str, Any]:
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
            all_results = await self._run_retrievers_batch(retriever_tasks)
            
            # # Step 4: Scrape additional details if scraper is available
            # try:
            #     scraped_results = scrape_results(all_results)
            #     if scraped_results != all_results:  # If scraper modified results
            #         all_results = scraped_results
            #         logger.info("Results enhanced with scraping")
            # except Exception as e:
            #     logger.warning(f"Scraping failed, continuing with original results: {str(e)}")
            
            # print("HERE#################", len(all_results))
            # print(all_results)
            
            # Step 5: Organize and filter results
            # organized_results = self._filter_and_organize_results(all_results)
            
            # logger.info(f"Planner agent completed. Found {organized_results['retriever_summary']['total_articles']} total articles")
            
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