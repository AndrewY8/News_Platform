"""Topic Agent Prompts"""

TOPIC_EXTRACTION_PROMPT = """Current date: {current_date}

Company: {company_name}
Business Areas: {business_areas}
Current Status: {current_status}

Search Results:
{formatted_results}

Extract important topics that could impact this company. For each topic, provide the most specific reasons why this news is important (2-3 sentences max).

IMPORTANT - You must cite your sources using article indices:
- For each topic, specify which articles support it using source_article_indices
- Use the Article numbers (0, 1, 2, etc.) shown above
- Only include articles that directly relate to and support the topic
- At least one article index is required per topic

Requirements:
- For urgency, use: "high", "medium", or "low"
- Confidence should be between 0.0 and 1.0
- Sources should be URLs from the search results that support the topic
- Subtopics should be related smaller topics or aspects
- source_article_indices: array of article numbers (e.g., [0, 2, 5]) that provide evidence for this topic"""

TOPIC_MERGE_PROMPT = """Company: {company_name}

EXISTING TOPICS IN MEMORY:
{existing_formatted}

NEW TOPICS TO MERGE:
{new_formatted}

**INTELLIGENT TOPIC ORGANIZATION PROTOCOL**

Choose the appropriate action based on the hierarchical relationship between topics:

**MERGE CRITERIA** (action: "merge") - Same scope, different angles:
- Topics are essentially THE SAME business theme with different perspectives
- Both topics address the same strategic question or business challenge
- New topic is an update, continuation, or alternative view of existing topic
- Combined topic creates a more complete picture of the same issue
- Examples of MERGE cases:
  * "Q3 Financial Results" + "Q3 Earnings Analysis" → MERGE (same event)
  * "AI Product Development" + "AI Innovation Strategy" → MERGE (same initiative)
  * "Supply Chain Issues" + "Logistics Disruptions" → MERGE (same problem)

**ADD_SUBTOPIC CRITERIA** (action: "add_subtopic") - Hierarchical relationship:
- New topic is a SPECIFIC COMPONENT or SUBSET of an existing broader topic
- New topic provides granular detail about one aspect of the parent topic
- Parent topic would benefit from this specific dimension being tracked separately
- Enables drilling down from high-level topic to specific implementation
- Examples of ADD_SUBTOPIC cases:
  * "Apple AI Strategy" + "Apple AI Chip Development" → ADD_SUBTOPIC (chips are part of AI strategy)
  * "Financial Performance" + "iPhone 15 Sales Data" → ADD_SUBTOPIC (iPhone sales contribute to financial performance)
  * "Market Expansion" + "European Operations Launch" → ADD_SUBTOPIC (Europe is part of expansion)
  * "Digital Transformation" + "Cloud Migration Project" → ADD_SUBTOPIC (cloud is part of transformation)

**ADD CRITERIA** (action: "add") - Completely independent topics:
- Topic addresses an entirely DIFFERENT business area, risk, or opportunity
- NO hierarchical or semantic relationship to existing topics
- Topic represents a distinct strategic focus requiring separate analysis
- Examples of ADD cases:
  * "AI Strategy" + "Regulatory Compliance" → ADD (different business areas)
  * "Financial Performance" + "Environmental Sustainability" → ADD (different focus areas)

**SKIP CRITERIA** (action: "skip") - Redundant or low-value:
- Topic is essentially duplicate information already captured
- Topic provides no new material insights
- Topic is too generic or speculative

**DECISION HIERARCHY:**
1. **First ask**: Is this the same topic from a different angle? → MERGE
2. **Then ask**: Is this a specific part of a broader existing topic? → ADD_SUBTOPIC
3. **Then ask**: Is this a completely independent business area? → ADD
4. **Finally**: Does this add any new value? If not → SKIP

For each decision, specify the semantic overlap percentage and explain why the topics should/shouldn't be consolidated."""

TOPIC_COMBINATION_PROMPT = """You are merging two business topics that have been identified as semantically similar. Create a comprehensive, unified topic that captures the full scope of both original topics.

EXISTING TOPIC:
Name: {existing_name}
Description: {existing_description}
Business Impact: {existing_impact}
Urgency: {existing_urgency}
Confidence: {existing_confidence}

NEW TOPIC TO MERGE:
Name: {new_name}
Description: {new_description}
Business Impact: {new_impact}
Urgency: {new_urgency}
Confidence: {new_confidence}

Create a merged topic that:
1. **Name**: Crafts a comprehensive name that encompasses both topic scopes
2. **Description**: Combines insights from both descriptions into a richer, more complete narrative
3. **Business Impact**: Synthesizes both impact assessments into a unified analysis
4. **Urgency**: Selects the higher urgency level (high > medium > low) as combined topics increase importance
5. **Confidence**: Uses the higher confidence score as more evidence increases reliability

**Guidelines:**
- Name should be concise but capture the broader scope (max 80 characters)
- Description should integrate key insights from both topics (2-3 sentences)
- Business impact should reflect the combined strategic implications
- Consider how the merger creates a more comprehensive view of the business theme
- Maintain professional, analytical tone focused on investment/business relevance

Provide the merged topic information in the specified JSON format."""