# --- Task planner for local retrievers ---
import logging
from typing import List, Tuple, Any
try:
    from ..prompts import create_sec_focused_query, create_breaking_news_query, create_multi_source_query
except ImportError:
    # Fallback functions if the specialized prompt functions don't exist yet
    def create_sec_focused_query(query: str) -> str:
        return f"SEC filings financial documents regulatory {query}"
    
    def create_breaking_news_query(query: str) -> str:
        return f"breaking news latest urgent {query}"
    
    def create_multi_source_query(query: str) -> str:
        return f"multiple sources verification {query}"

# Import all available retrievers
from ..retrievers.custom.custom import CustomRetriever
from ..retrievers.duckduckgo.duckduckgo import DuckDuckGoRetriever
from ..retrievers.exa.exa import ExaRetriever
from ..retrievers.google.google import GoogleRetriever
# from ..retrievers.mcp.retriever import MCPRetriever
from ..retrievers.searchapi.searchapi import SearchAPIRetriever
from ..retrievers.searx.searx import SearxRetriever
from ..retrievers.serpapi.serpapi import SerpAPIRetriever
from ..retrievers.serper.serper import SerperRetriever
from ..retrievers.tavily.tavily_search import TavilyRetriever

logger = logging.getLogger(__name__)

# Define retriever priorities and capabilities
RETRIEVER_CONFIG = {
    'TavilyRetriever': {
        'priority': 1,
        'specialties': ['breaking_news', 'real_time'],
        'rate_limit': 5  # requests per minute
    },
    'GoogleRetriever': {
        'priority': 2, 
        'specialties': ['comprehensive', 'sec_filings'],
        'rate_limit': 10
    },
    'SerperRetriever': {
        'priority': 3,
        'specialties': ['news', 'multi_source'],
        'rate_limit': 15
    },
    'SerpAPIRetriever': {
        'priority': 4,
        'specialties': ['structured_data', 'financial'],
        'rate_limit': 10
    },
    'ExaRetriever': {
        'priority': 5,
        'specialties': ['semantic_search', 'content_quality'],
        'rate_limit': 20
    },
    'SearchAPIRetriever': {
        'priority': 6,
        'specialties': ['general_news', 'coverage'],
        'rate_limit': 25
    },
    'DuckDuckGoRetriever': {
        'priority': 7,
        'specialties': ['privacy', 'unbiased'],
        'rate_limit': 30
    },
    'SearxRetriever': {
        'priority': 8,
        'specialties': ['aggregated', 'privacy'],
        'rate_limit': 20
    },
    'CustomRetriever': {
        'priority': 9,
        'specialties': ['custom_logic', 'specialized'],
        'rate_limit': 15
    },
    'MCPRetriever': {
        'priority': 10,
        'specialties': ['protocol_specific', 'structured'],
        'rate_limit': 10
    }
}

def get_retriever_tasks(query: str) -> List[Tuple[Any, str]]:
    """
    Create specialized tasks for different retrievers based on their strengths.
    
    Args:
        query (str): The augmented query from prompts.py
        
    Returns:
        List[Tuple[Any, str]]: List of (retriever_instance, specialized_task) tuples
    """
    retriever_classes = [
        CustomRetriever,
        DuckDuckGoRetriever, 
        ExaRetriever,
        GoogleRetriever,
        # MCPRetriever,
        SearchAPIRetriever,
        SearxRetriever,
        SerpAPIRetriever,
        SerperRetriever,
        TavilyRetriever,
    ]
    
    tasks = []
    
    # Create different query variations for different purposes
    sec_query = create_sec_focused_query(query)
    breaking_news_query = create_breaking_news_query(query)
    multi_source_query = create_multi_source_query(query)
    
    for cls in retriever_classes:
        try:
            retriever = cls()
            retriever_name = cls.__name__
            
            # Assign specialized tasks based on retriever capabilities
            if retriever_name in ['TavilyRetriever', 'SerperRetriever']:
                # These are good for real-time breaking news
                tasks.append((retriever, breaking_news_query))
            elif retriever_name in ['GoogleRetriever', 'SerpAPIRetriever']:
                # These are good for SEC filings and structured data
                tasks.append((retriever, sec_query))
            elif retriever_name in ['ExaRetriever', 'SearchAPIRetriever']:
                # These are good for multi-source verification
                tasks.append((retriever, multi_source_query))
            else:
                # Default to the main augmented query
                tasks.append((retriever, query))
                
        except Exception as e:
            logger.error(f"Failed to initialize {cls.__name__}: {str(e)}")
            continue
    
    logger.info(f"Created {len(tasks)} retriever tasks")
    return tasks

def get_priority_retrievers(query: str, max_retrievers: int = 5) -> List[Tuple[Any, str]]:
    """
    Get only the highest priority retrievers for faster results.
    
    Args:
        query (str): The query to search for
        max_retrievers (int): Maximum number of retrievers to use
        
    Returns:
        List[Tuple[Any, str]]: Prioritized list of retriever tasks
    """
    all_tasks = get_retriever_tasks(query)
    
    # Sort by priority based on config
    def get_priority(task_tuple):
        retriever, _ = task_tuple
        retriever_name = retriever.__class__.__name__
        return RETRIEVER_CONFIG.get(retriever_name, {}).get('priority', 999)
    
    sorted_tasks = sorted(all_tasks, key=get_priority)
    return sorted_tasks[:max_retrievers]

def get_specialized_retrievers(specialty: str, query: str) -> List[Tuple[Any, str]]:
    """
    Get retrievers that specialize in a particular type of search.
    
    Args:
        specialty (str): The type of specialty needed ('breaking_news', 'sec_filings', etc.)
        query (str): The query to search for
        
    Returns:
        List[Tuple[Any, str]]: List of specialized retriever tasks
    """
    all_tasks = get_retriever_tasks(query)
    specialized_tasks = []
    
    for retriever, task in all_tasks:
        retriever_name = retriever.__class__.__name__
        retriever_specialties = RETRIEVER_CONFIG.get(retriever_name, {}).get('specialties', [])
        
        if specialty in retriever_specialties:
            specialized_tasks.append((retriever, task))
    
    return specialized_tasks

def get_retriever_info():
    """
    Get information about all available retrievers and their capabilities.
    
    Returns:
        dict: Information about retrievers and their configurations
    """
    return RETRIEVER_CONFIG