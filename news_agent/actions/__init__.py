from .retriever import (
    get_retriever_tasks, 
    get_priority_retrievers, 
    get_specialized_retrievers,
    get_retriever_info
)

# Import functions that are currently commented out but listed in __all__
# These should be implemented when the corresponding modules are available
try:
    from .query_processing import plan_research_outline, get_search_results
except ImportError:
    def plan_research_outline(*args, **kwargs):
        raise NotImplementedError("query_processing module not yet implemented")
    
    def get_search_results(*args, **kwargs):
        raise NotImplementedError("query_processing module not yet implemented")

try:
    from .agent_creator import extract_json_with_regex, choose_agent
except ImportError:
    def extract_json_with_regex(*args, **kwargs):
        raise NotImplementedError("agent_creator module not yet implemented")
    
    def choose_agent(*args, **kwargs):
        raise NotImplementedError("agent_creator module not yet implemented")

try:
    from .web_scraping import scrape_urls, summarize_url, extract_headers, extract_sections
except ImportError:
    def scrape_urls(*args, **kwargs):
        raise NotImplementedError("web_scraping module not yet implemented")
    
    def summarize_url(*args, **kwargs):
        raise NotImplementedError("web_scraping module not yet implemented")
    
    def extract_headers(*args, **kwargs):
        raise NotImplementedError("web_scraping module not yet implemented")
    
    def extract_sections(*args, **kwargs):
        raise NotImplementedError("web_scraping module not yet implemented")

# Legacy function names for backward compatibility
def get_retriever(*args, **kwargs):
    """Legacy function - use get_retriever_tasks instead"""
    return get_retriever_tasks(*args, **kwargs)

def get_retrievers(*args, **kwargs):
    """Legacy function - use get_priority_retrievers instead"""
    return get_priority_retrievers(*args, **kwargs)

__all__ = [
    # Main retriever functions
    "get_retriever_tasks",
    "get_priority_retrievers", 
    "get_specialized_retrievers",
    "get_retriever_info",
    
    # Legacy compatibility
    "get_retriever",
    "get_retrievers",
    
    # Placeholder functions (not yet implemented)
    "get_search_results",
    "plan_research_outline",
    "extract_json_with_regex",
    "choose_agent",
    "scrape_urls",
    "summarize_url",
    "extract_headers",
    "extract_sections"
]