"""Ranking Agent Prompts"""

IMPACT_ASSESSMENT_PROMPT = """Current date: {current_date}

Company: {company_name}
Business Areas: {business_areas}
Current Status: {current_status}

Topic to Assess:
Name: {topic_name}
Description: {topic_description}
Business Impact: {topic_business_impact}
Urgency: {topic_urgency}
Confidence: {topic_confidence}

Assess the potential impact of this topic on the company. Rate each dimension from 0.0 to 1.0:

Financial Impact: Direct effect on revenue, costs, profitability, or valuation
Operational Impact: Effect on day-to-day operations, processes, or capabilities
Strategic Impact: Long-term competitive position, market share, or strategic goals
Urgency Factor: How time-sensitive this topic is for the company

Provide reasoning for your assessment in 2-3 sentences."""