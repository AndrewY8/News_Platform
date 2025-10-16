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

# Analytical Reasoning Framework
ANALYTICAL_REASONING_FRAMEWORK = """
Think like a financial analyst conducting deep research on {target}. Apply these analytical lenses:

1. CAUSAL ANALYSIS - What's driving this? What will it drive next?
   • Identify cause → effect → consequence chains
   • Example: "Fed rate hike → higher borrowing costs → reduced consumer spending → iPhone sales pressure"

2. CROSS-MARKET CONNECTIONS - How do different markets/sectors interconnect?
   • Connect seemingly unrelated events across domains
   • Example: "Banking crisis → corporate CFOs hoard cash → delayed IT spending → cloud revenue slowdown"

3. SECOND-ORDER EFFECTS - What happens after the obvious first impact?
   • Look beyond immediate effects to downstream consequences
   • Example: "Chip shortage → production delays AND R&D timeline shifts AND competitive positioning changes"

4. CONTRARIAN THINKING - What is consensus missing?
   • Challenge market assumptions and explore overlooked risks/opportunities
   • Example: "AI hype is obvious, but what about AI infrastructure costs and margin pressure?"

5. FORWARD-LOOKING ANALYSIS - What comes next in this narrative?
   • Anticipate next developments and strategic responses
   • Example: "If supply chain issues persist, what strategic shifts might management announce?"

6. MULTI-STAKEHOLDER IMPACT - Who else is affected?
   • Trace impacts across suppliers, customers, competitors, regulators
   • Example: "Regulatory change affects not just the company, but entire ecosystem dynamics"
"""

CREATIVE_QUERY_GENERATION_PROMPT_COMPANY = """Current date: {current_date}

Company: {company_name}
Business Areas: {business_areas}

{analytical_framework}

CONTEXT - TOPICS DISCOVERED SO FAR:
{topics_summary}

PREVIOUS ITERATION INSIGHTS:
{previous_insights}

---

YOUR MISSION: You are a creative financial analyst tasked with finding NON-OBVIOUS connections and insights.

CREATIVITY REQUIREMENTS:
- DO NOT just search for company name plus topic - that is too obvious
- MAKE UNEXPECTED CONNECTIONS between seemingly unrelated markets and events
- THINK LIKE A CONTRARIAN - what is everyone else missing
- ASK WHAT IF questions - explore alternative scenarios
- CONNECT THE DOTS - how do macro events cascade into specific company impacts

REQUIRED QUERY CATEGORIES (generate 10-12 total queries):

1. **CAUSAL QUERIES (2-3 queries)**: What is REALLY causing this? What happens next?
   - Think: If X happened, what MUST have caused it? And if X is happening, what WILL happen?
   - Connect macro to micro: Fed policy to borrowing costs to consumer behavior to product demand
   - Example: labor market wage inflation service sector pricing power enterprise software renewal rates compression
   - BAD: MSFT revenue growth causes (too direct)
   - GOOD: remote work reversal commercial real estate recovery enterprise collaboration software demand shift

2. **CROSS-DOMAIN QUERIES (2-3 queries)**: Find connections NO ONE else is looking at
   - Think: What seemingly unrelated event could cascade into this company?
   - Look at: energy prices, commodity markets, regulatory changes in OTHER industries, geopolitical shifts
   - Example: European energy crisis data center power costs cloud infrastructure pricing Nordic expansion
   - BAD: tech sector impact MSFT (obvious)
   - GOOD: banking crisis CFO budget freeze discretionary IT spending SaaS renewal postponement 2025

3. **IMPLICATION QUERIES (2-3 queries)**: What is the SECOND and THIRD order consequence?
   - Think: Everyone sees X leads to Y, but what about X leads to Y leads to Z and beyond?
   - Trace the cascade: initial impact to business response to market reaction to competitive shift
   - Example: AI model training costs GPU shortage capacity constraints pricing power margin trajectory
   - BAD: AI impact on cloud (first-order, obvious)
   - GOOD: AI infrastructure capex surge free cash flow investor sentiment valuation multiple compression risk

4. **CONTRARIAN QUERIES (2 queries)**: What is the market getting WRONG?
   - Think: Everyone believes X, but what if Y is actually true?
   - Challenge assumptions: AI hype vs AI profitability, cloud growth vs cloud saturation
   - Example: generative AI enterprise adoption reality gap productivity gains measurement skepticism emerging
   - BAD: risks to MSFT growth (generic)
   - GOOD: Microsoft 365 Copilot pricing resistance enterprise budget constraints ROI proof demand slowdown

5. **FORWARD-LOOKING QUERIES (2-3 queries)**: What strategic move is coming NEXT?
   - Think: If I were the CEO facing X, what would I do? What will competitors do?
   - Anticipate: M&A targets, geographic expansion, product pivots, cost-cutting, restructuring
   - Example: OpenAI partnership tension Microsoft proprietary AI model development strategic alternatives 2025
   - BAD: MSFT future strategy (vague)
   - GOOD: enterprise AI spending slowdown Microsoft cloud bundling strategy margin defense pricing leverage

---

CRITICAL SEARCH OPTIMIZATION RULES:
- Each query MUST be under 400 characters (Tavily API hard limit)
- Use keyword-rich phrases, NOT questions (for example: impact of X on Y not How does X affect Y)
- Include temporal indicators: 2025, recent, latest, outlook, forecast
- Use specific industry terminology and financial keywords
- Make queries SEARCHABLE for news articles and analyst reports

EXAMPLES OF EXCELLENT ANALYTICAL QUERIES:

BAD (passive, generic):
Apple latest news
iPhone sales 2025
Apple stock price

GOOD (analytical, creative):
Apple supply chain diversification India Vietnam manufacturing geopolitical risk mitigation 2025
Fed interest rate policy consumer electronics financing demand correlation iPhone upgrade cycle
generative AI infrastructure costs margin pressure Apple services cloud revenue impact analysis
China App Store regulatory crackdown revenue exposure alternative growth strategies
Apple Vision Pro adoption enterprise market spatial computing competitive moat assessment
tariff policy semiconductor supply chain cost structure profitability headwinds

---

BEFORE YOU GENERATE QUERIES:
1. Review the topics already discovered above - DO NOT just search for more of the same
2. Think about what gaps exist - what haven't we explored yet?
3. Consider unconventional connections - what would surprise a typical analyst?
4. Focus on INSIGHTS not INFORMATION - we want analysis, not news summaries

FORBIDDEN PATTERNS (do NOT use these):
- company earnings (too obvious)
- company stock price (not analytical)
- company news 2025 (too generic)
- company plus any single keyword (not creative)

ENCOURAGED PATTERNS (use these):
- macro event - intermediate effect - company-specific impact (causal chains)
- unrelated industry trend - connection mechanism - business area impact (cross-domain)
- consensus view - contrarian indicator - alternative interpretation (contrarian)
- current development - logical next step - strategic response (forward-looking)

Now generate your 10-12 creative, non-obvious analytical search queries:"""

CREATIVE_QUERY_GENERATION_PROMPT_MACRO = """Current date: {current_date}

Macro Research Category: {category_name}
Focus Areas: {focus_areas}

{analytical_framework}

CONTEXT - TOPICS DISCOVERED SO FAR:
{topics_summary}

PREVIOUS ITERATION INSIGHTS:
{previous_insights}

---

YOUR MISSION: Generate ANALYTICAL search queries exploring market-wide implications and interconnections.

REQUIRED QUERY CATEGORIES (generate 10-12 total queries):

1. **MARKET CAUSALITY (2-3 queries)**: What's driving macro trends and what do they drive?
   - Example: "Fed rate path inflation expectations equity valuation multiples compression 2025"

2. **CROSS-ASSET CONNECTIONS (2-3 queries)**: How do different asset classes and markets interconnect?
   - Example: "Treasury yield curve inversion recession probability equity market volatility implications"

3. **POLICY IMPLICATIONS (2-3 queries)**: Second-order effects of policy changes on markets
   - Example: "fiscal stimulus debt ceiling negotiations market confidence investor positioning"

4. **CONTRARIAN MARKET VIEWS (1-2 queries)**: Challenge consensus market narratives
   - Example: "inflation peak narrative labor market tightness wage growth persistence risks"

5. **FORWARD MARKET OUTLOOK (2-3 queries)**: Anticipate next macro developments
   - Example: "central bank policy divergence currency volatility emerging markets capital flows 2025"

---

CRITICAL RULES:
- Under 400 characters per query
- Focus on MARKET-WIDE impacts (not company-specific)
- Use financial terminology: Fed, rates, inflation, GDP, yields, volatility, etc.
- Include timeframe: "{current_year}", "outlook", "forecast", "expectations"

Generate your 10-12 analytical macro queries now:"""