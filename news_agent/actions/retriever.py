# --- Task planner for local retrievers ---
import logging
from typing import List, Tuple, Any
from ..prompts import pick_retriever

# Import all available retrievers
from ..retrievers.custom.custom import CustomRetriever
from ..retrievers.duckduckgo.duckduckgo import DuckDuckGoRetriever
from ..retrievers.exa.exa import ExaRetriever
from ..retrievers.google.google import GoogleRetriever
from ..retrievers.searchapi.searchapi import SearchAPIRetriever
from ..retrievers.searx.searx import SearxRetriever
from ..retrievers.serpapi.serpapi import SerpAPIRetriever
from ..retrievers.serper.serper import SerperRetriever
from ..retrievers.tavily.tavily_search import TavilyRetriever
from ..retrievers.EDGAR.EDGAR import EDGARRetriever

logger = logging.getLogger(__name__)

def get_retriever_tasks(queries: str, client) -> List[Tuple[Any, str]]:
    """
    Create specialized tasks for different retrievers based on their strengths.
    
    Args:
        query (str): The augmented query from prompts.py
        
    Returns:
        List[Tuple[Any, str]]: List of (retriever_instance, specialized_task) tuples
    """

    retriever_classes = [
        TavilyRetriever,
        EDGARRetriever,
        SerperRetriever,
        GoogleRetriever,
        SerpAPIRetriever,
        ExaRetriever,
        SearchAPIRetriever,
    ]
    
    tasks = []

    for query in queries:
        model = client.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(pick_retriever(query, ['TavilyRetriever']))
        print("PICK RETRIEVER TEXT")
        print(response.text)
        index = int(response.text)
        tasks.append((retriever_classes[index], query))
    return tasks