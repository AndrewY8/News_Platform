"""Search Agent Prompts"""

QUERY_GENERATION_PROMPT = """Current date: {current_date}

Company: {company_name}
Business Areas: {business_areas}

Questions to research:
{questions_text}

Convert these questions into effective web search queries that will find the most relevant recent information. Each query should be:
- Specific and targeted
- Include relevant keywords for the company's industry
- Optimized for finding recent news and developments
- Clear about what information is expected

Generate 3-5 search queries maximum."""

QUESTION_GENERATION_PROMPT = """Current date: {current_date}

Company: {company_name}
Business Areas: {business_areas}
Search Iteration: {iteration}

Relevant Topics:
{topics_text}

Generate specific research questions that would help us find the most important recent information about these topics as they relate to {company_name}.

Focus on:
- Recent developments and news
- Impact on the company's business
- Competitive implications
- Regulatory or market changes
- Future outlook and trends

Generate 5-8 high-priority questions."""

EARNINGS_ANALYSIS_PROMPT = """You are an experienced financial analyst who has listened to many earnings transcript calls.

Please extract the key ideas from this transcript that you felt were the most interesting and could most affect the company.

Some examples of possible key points are listed below:
-- Apple has seen revenue growth because of X product, or Apple has performed poorly in X segment because of Y reason.
-- Apple released the following product this quarter _____
-- Apple is affected politically by this action _____
-- Apple is undergoing a M&A transaction, spinoff or related transaction for X reason
-- Apple sees risks regarding its supply chain because there are new dynamics regarding tariff pricing
-- Apple is building a new factory in X to build Y."""