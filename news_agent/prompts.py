# --- Enhanced query augmentation for planner agent ---

def augment_query(query: str) -> str:
    """
    Augment the user query for better retrieval focusing on news and SEC filings.
    
    Args:
        query (str): The original user query
        
    Returns:
        str: Augmented query with specific instructions for retrievers
    """
    return f"""
RESEARCH QUERY: "{query}"

PRIORITY SEARCH OBJECTIVES:
1. BREAKING NEWS: Find the most recent breaking news and developing stories
2. MULTI-SOURCE VERIFICATION: Get the same story from multiple reputable news sources
3. SEC FILINGS: Locate relevant 10-K, 10-Q, 8-K, and other SEC documents
4. FINANCIAL NEWS: Include earnings reports, analyst coverage, market impact
5. COMPREHENSIVE COVERAGE: Include international, local, and specialized sources

SEARCH TERMS TO PRIORITIZE:
- Breaking news + "{query}"
- Latest news + "{query}" 
- "{query}" + SEC filings
- "{query}" + 10-K OR 10-Q OR 8-K
- "{query}" + earnings OR financial results
- "{query}" + analyst report OR rating
- "{query}" + regulatory filing
- "{query}" + press release

REQUIRED DATA POINTS FOR EACH RESULT:
- Headline/Title
- Publication date and time
- News source/publisher
- Direct URL to article
- Brief summary/description
- For SEC filings: Filing type, filing date, document URL

OUTPUT REQUIREMENTS:
- Return results in JSON format only
- Include multiple sources for major stories
- Prioritize recency (last 24-48 hours for breaking news)
- Include both free and premium source links where available
- Mark SEC.gov and EDGAR links clearly
- Ensure URLs are direct links to articles/documents

SEARCH STRATEGY:
1. Start with broad news search for recent developments
2. Search specifically for SEC filings and regulatory documents  
3. Look for multiple sources covering the same story
4. Include financial/business news sources
5. Check for official statements and press releases
6. Verify information across sources

Focus on factual reporting from established news sources, official SEC filings, and verified press releases. Avoid speculation, opinion pieces, or unverified social media content unless clearly marked.
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
