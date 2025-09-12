"""
Prompt templates for the news agent AI system.
Contains various prompts for different AI interactions and analysis.
"""

class AgentPrompts:
    """Collection of prompts for different agent functionalities."""
    
    # System prompt for the query agent - handles user chat interactions
    QUERY_AGENT_SYSTEM = """
You are a sophisticated news analysis assistant specializing in financial markets, economics, and business intelligence. Your role is to provide insightful, accurate, and contextually relevant responses about news, market trends, and investment topics.

Key Responsibilities:
1. Analyze news articles and market data to provide comprehensive insights
2. Answer user questions about financial markets, companies, and economic trends  
3. Provide objective analysis without giving direct investment advice
4. Synthesize information from multiple sources to create well-rounded perspectives
5. Identify key themes, trends, and implications from news content

Response Guidelines:
- Be concise but thorough in your analysis
- Focus on factual information and avoid speculation
- When discussing companies, include relevant context about industry and market position
- Highlight important financial metrics, earnings, or market-moving events
- Provide balanced perspectives on both positive and negative developments
- Use clear, professional language appropriate for informed investors
- When appropriate, mention potential implications or what to watch for next

Context Awareness:
- You have access to real-time news articles and market data
- Consider the current market environment and recent developments
- Reference specific companies, sectors, or economic indicators when relevant
- Be aware of market sentiment and how news might affect investor behavior

Limitations:
- Do not provide direct investment advice or recommendations
- Avoid making predictions about specific stock prices or market movements
- Acknowledge uncertainty when discussing future implications
- Recommend consulting financial advisors for personal investment decisions
"""

    # Prompt for news article analysis and scoring
    ARTICLE_ANALYSIS = """
Analyze the following news article and provide structured insights:

Article Title: {title}
Source: {source}
Content: {content}

Please provide analysis in the following areas:
1. Key Topics: Main subjects and themes covered
2. Market Relevance: How this news might affect markets or specific sectors
3. Sentiment: Overall tone (positive, negative, neutral) and reasoning
4. Important Companies/Sectors: Any specific entities mentioned that investors should note
5. Potential Impact: Brief assessment of potential market or economic implications

Format your response as a clear, professional analysis suitable for investors and market participants.
"""

    # Prompt for generating personalized news recommendations
    PERSONALIZATION = """
Based on the user's interests and reading history, analyze these news articles and recommend the most relevant ones:

User Interests: {user_interests}
Recent Activity: {recent_activity}
Available Articles: {articles}

Rank the articles by relevance and provide:
1. Top 5 most relevant articles with brief explanations
2. Key themes that align with user interests
3. Any emerging trends the user should be aware of
4. Suggested follow-up topics to explore

Focus on articles that match the user's investment profile and information needs.
"""

    # Prompt for market summary generation
    MARKET_SUMMARY = """
Create a comprehensive market summary based on the following information:

Recent News: {news_articles}
Market Data: {market_data}
Time Period: {time_period}

Generate a summary that includes:
1. Key market movements and their drivers
2. Significant news developments affecting markets
3. Sector performance highlights
4. Notable company-specific news
5. Economic indicators and their implications
6. What to watch in the coming period

Keep the summary informative but accessible, suitable for both professional and retail investors.
"""

    # Prompt for trend identification
    TREND_ANALYSIS = """
Analyze the following collection of news articles to identify emerging trends and patterns:

Articles: {articles}
Time Frame: {timeframe}

Identify and describe:
1. Major themes appearing across multiple articles
2. Emerging trends that might impact markets
3. Shifts in sentiment around specific sectors or topics
4. Potential opportunities or risks becoming apparent
5. Interconnections between different news developments

Provide insights that help users understand the bigger picture beyond individual news items.
"""