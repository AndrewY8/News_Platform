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
1. BREAKING NEWS: Generate search queries to identify the most recent breaking news and developing stories relevant to the research query.
2. SEC FILINGS: Generate search queries to locate relevant 10-K, 10-Q, 8-K, and other SEC documents pertinent to the research query.
3. FINANCIAL NEWS: Generate search queries to find earnings reports, analyst coverage, and market impact related to the research query.
4. COMPREHENSIVE COVERAGE: Generate search queries to ensure the research includes international, local, and specialized sources for the research query.

Output each generated search query on a new line, prefixed with a unique identifier that also indicates the objective it addresses. Use "@@@" as the separator between this identifier and the search query itself.

Example Output Format:
BREAKING_NEWS_1@@@"{query}" breaking news
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
- `topic`: A concise, specific keyword or phrase (e.g., "financial news", "tech reviews", "medical research"). Default: "general".
- `days`: An integer representing the recency of information (e.g., 7 for last week, 365 for last year). Default: 30.
- `max_results`: An integer for the maximum number of search results to return (up to Tavily's limit). Default: 10.
- `include_answer`: `True` or `False`. Set to `True` if the query explicitly asks for a direct answer or summary, or if a concise factual answer is likely sufficient. Default: `False`.

Analyze the `User Query` below. For each parameter, output the most suitable value based on the query's explicit and implicit intent.

**If a parameter's value cannot be inferred or is not relevant, use its default value.**

**Output Format:** Provide only a valid JSON object with the parameter names as keys and their inferred values. Do NOT include any other text, explanations, or formatting outside the JSON object.

User Query: "{query}"

Output JSON:
"""

# def create_sec_focused_query(query: str) -> str:
#     """
#     Create a query specifically optimized for SEC filing retrieval.
    
#     Args:
#         query (str): The original query
        
#     Returns:
#         str: SEC-focused query string
#     """
#     return f"""
# SEC FILING SEARCH: "{query}"

# TARGET DOCUMENTS:
# - 10-K (Annual Reports)
# - 10-Q (Quarterly Reports) 
# - 8-K (Current Reports)
# - DEF 14A (Proxy Statements)
# - S-1/S-3 (Registration Statements)
# - 13F (Institutional Holdings)
# - 4 (Insider Trading)

# SEARCH LOCATIONS:
# - SEC.gov EDGAR database
# - Company investor relations pages
# - Financial news with SEC document links
# - Regulatory news sources

# REQUIRED FIELDS:
# - Filing type
# - Filing date
# - Company name/ticker
# - Document title
# - Direct EDGAR URL
# - Key sections/highlights
# - Filing summary

# Return only official SEC documents and verified regulatory filings.
# """

# def create_breaking_news_query(query: str) -> str:
#     """
#     Create a query optimized for breaking news retrieval.
    
#     Args:
#         query (str): The original query
        
#     Returns:
#         str: Breaking news focused query string
#     """
#     return f"""
# BREAKING NEWS SEARCH: "{query}"

# PRIORITY SOURCES:
# - Reuters, AP, Bloomberg, WSJ, NYT
# - Financial Times, CNBC, CNN Business
# - Industry-specific publications
# - Official company/government press releases
# - Wire services and news agencies

# TIME FILTERS:
# - Last 24 hours (highest priority)
# - Last 48 hours (medium priority) 
# - Last week (background context)

# REQUIRED ELEMENTS:
# - Timestamp of publication
# - Multiple source verification
# - Direct article URLs
# - Key quotes and facts
# - Related story links

# SEARCH TERMS:
# - "breaking" + "{query}"
# - "developing" + "{query}"
# - "just in" + "{query}"
# - "urgent" + "{query}"
# - "live updates" + "{query}"

# Focus on verified, time-sensitive information from credible news sources.
# """

# def create_multi_source_query(query: str) -> str:
#     """
#     Create a query designed to find multiple sources covering the same story.
    
#     Args:
#         query (str): The original query
        
#     Returns:
#         str: Multi-source verification query
#     """
#     return f"""
# MULTI-SOURCE VERIFICATION: "{query}"

# OBJECTIVE: Find the same story covered by multiple reputable sources

# TARGET SOURCE TYPES:
# - Major newspapers (WSJ, NYT, WaPo, FT)
# - Wire services (Reuters, AP, Bloomberg)
# - Business publications (Forbes, Fortune, Business Insider)
# - Industry publications (sector-specific)
# - International sources (BBC, Guardian, etc.)
# - Local/regional sources (when relevant)

# VERIFICATION POINTS:
# - Cross-reference key facts across sources
# - Compare quotes and statements
# - Note timing differences in reporting
# - Identify unique angles or insights
# - Flag any discrepancies

# SEARCH APPROACH:
# 1. Search for main story across all source types
# 2. Look for follow-up reporting and analysis
# 3. Find original source materials (press releases, filings)
# 4. Include expert commentary and analysis
# 5. Check for corrections or updates

# Return articles that cover the same core story from different perspectives and sources.
# """


def create_sec_focused_query(query: str) -> str:
    return f'SEC SEARCH: "{query}". Target 10-K, 10-Q, 8-K, DEF14A, S-1/S-3, 13F, Form 4. Sources: SEC EDGAR, investor pages, verified filings. Return filing type, date, company, title, URL, highlights, summary.'

def create_breaking_news_query(query: str) -> str:
    return f'BREAKING NEWS: "{query}". Sources: Reuters, AP, Bloomberg, WSJ, NYT, FT, CNBC, press releases. Last 48h priority. Include timestamp, URLs, summaries, key quotes. Terms: breaking, developing, just in, urgent, live updates.'

def create_multi_source_query(query: str) -> str:
    return f'MULTI-SOURCE: "{query}". Find same story from WSJ, NYT, Reuters, AP, Bloomberg, Forbes, industry/intl/local sources. Cross-check facts, quotes, timing. Include press releases, filings, analysis, and note discrepancies.'
