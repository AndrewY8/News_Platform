# --- Enhanced query augmentation for planner agent ---

def augment_query(query: str, n = 1) -> str:
    """
    Augment the user query for better retrieval focusing on news and SEC filings.
    
    Args:
        query (str): The original user query
        n (int): number of questions to generate
        
    Returns:
        str: Augmented query with specific instructions for retrievers
    """
    return f"""
You are an analyst that generates {n} distinct search queries designed to thoroughly cover the PRIORITY SEARCH OBJECTIVES for the given research query. Each generated query should be optimized for direct use in a search engine.

RESEARCH QUERY: "{query}"

PRIORITY SEARCH OBJECTIVES:
1. SEC FILINGS: Generate search queries to locate relevant 10-K, 10-Q, 8-K, and other SEC documents pertinent to the research query.
2. FINANCIAL NEWS: Generate search queries to find earnings reports, analyst coverage, and market impact related to the research query.
3. COMPREHENSIVE COVERAGE: Generate search queries to ensure the research includes international, local, and specialized sources for the research query.

Output each generated search query on a new line, prefixed with a unique identifier that also indicates the objective it addresses. Use "@@@" as the separator between this identifier and the search query itself.

Example Output Format:
SEC_FILINGS_1@@@"{query}" 10-K OR 10-Q OR 8-K
FINANCIAL_NEWS_1@@@"{query}" earnings reports
"""

def pick_retriever(query, retriever_options):
   return f"""
You are a routing agent for an information retrieval system. Your task is to select the single most appropriate web search retriever for a given user query from the available options.

Return an index from 0 to {len(retriever_options) - 1} indicating which retriever is the most appropriate for the query: "{query}". Consider the general nature of the query and which web search tool would likely provide the most comprehensive or relevant results. If the query doesn't strongly favor one over the others, select the first general-purpose option (index 0).

ONLY RETURN THE SINGLE NUMERIC INDEX.

Example:
Query: "When was the last time the Philadelphia Eagles won the Super Bowl?"
Retriever Options: ["TavilyRetriever", "SerperSearch", "GoogleSearch"]
Expected Output: 0 (assuming Tavily is the default general-purpose web search)
""" 

def pick_tavily_params(query):
    return f"""
You are an intelligent Tavily Search Query Parameter Planner. Your task is to analyze a given user query and determine the most appropriate custom parameter values for a Tavily API call.

The available parameters and their types are:
- `search_depth`: "basic" (quick, fewer results) or "advanced" (more comprehensive, deeper search). Default: "basic".
- `topic`: `general`, `finance`, or `news`. Default: "news".
- `days`: An integer representing the recency of information (e.g., 7 for last week, 365 for last year). Default: 30.
- `max_results`: An integer for the maximum number of search results to return (up to Tavily's limit). Default: 10.
- `include_answer`: `True` or `False`. Set to `True` if the query explicitly asks for a direct answer or summary, or if a concise factual answer is likely sufficient. Default: `False`.

Analyze the `User Query` below. For each parameter, output the most suitable value based on the query's explicit and implicit intent.

**If a parameter's value cannot be inferred or is not relevant, use its default value.**

**Output Format:** Provide only a valid JSON object with the parameter names as keys and their inferred values. Do NOT include any other text, explanations, or formatting outside the JSON object.

User Query: "{query}"

Output JSON:
"""