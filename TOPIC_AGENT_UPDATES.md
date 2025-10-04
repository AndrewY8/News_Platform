# TopicAgent Updates - Unified Context Support

## Changes Made

### 1. **Imports Updated**
- ✅ Added `ResearchContext, ResearchType` to imports from interfaces
- ✅ Removed duplicate `CompanyContext` definition

### 2. **Method Signatures Updated**
All methods now accept `ResearchContext`:

1. ✅ `extract_topics(search_results, context: ResearchContext, iteration, company_id)`
2. ✅ `update_memory(new_topics, context: ResearchContext)`
3. ✅ `_build_extraction_prompt(search_results, context: ResearchContext)`
4. ✅ `_build_merge_prompt(existing_topics, new_topics, context: ResearchContext)`

### 3. **Adaptive Topic Extraction Prompts**

The `_build_extraction_prompt` method now branches based on research type:

**For Company Research:**
```python
if research_type.value == "company":
    return TOPIC_EXTRACTION_PROMPT.format(
        current_date=current_date,
        company_name=context.get_display_name(),
        business_areas=', '.join(context.get_focus_areas()),
        current_status=...,
        formatted_results=formatted_results
    )
```

Uses existing company-specific prompt template focusing on:
- Business impact on specific company
- Company operations and strategy
- Product/service developments

**For Macro/Political Research:**
```python
else:
    return self._build_macro_extraction_prompt(...)
```

Uses NEW macro-specific prompt focusing on:
- **MARKET-WIDE implications** (not company-specific)
- **Investor strategy** and portfolio impact
- **Broad economic/political themes**

### 4. **New Macro Extraction Prompt**

Created `_build_macro_extraction_prompt()` with distinct requirements:

```python
def _build_macro_extraction_prompt(self, search_results, context, current_date, formatted_results):
    return f"""Current date: {current_date}

Macro Research Category: {context.get_display_name()}
Focus Areas: {', '.join(context.get_focus_areas())}

Search Results:
{formatted_results}

Extract important MACRO/POLITICAL topics that could impact financial markets broadly.

Requirements:
- Focus on MARKET-WIDE implications, not company-specific
- For "business_impact", explain how this affects MARKETS BROADLY and investor strategy
- For urgency: "high" (immediate market impact), "medium" (developing), "low" (background)

Examples of good macro topics:
- "Federal Reserve Rate Policy Shift" ✅
- "Apple affected by Fed policy" ❌
- "Inflation Concerns Driving Market Volatility" ✅
- "Inflation impacting specific retailers" ❌
```

### 5. **Key Differences: Company vs Macro Topics**

| Aspect | Company Topics | Macro Topics |
|--------|---------------|--------------|
| **Focus** | Company-specific impact | Market-wide implications |
| **business_impact** | "How this affects [Company]'s operations" | "How this affects MARKETS and investor strategy" |
| **Examples** | "Apple AI Strategy", "Tesla Production Capacity" | "Fed Policy Shift", "Election Market Impact" |
| **Urgency** | Based on company operations | Based on market-wide impact |
| **Subtopics** | Product lines, business divisions | Economic indicators, policy aspects |

## Verification

✅ No unhandled `company_context` references
✅ All methods use `context: ResearchContext`
✅ Adaptive prompts based on `context.get_research_type()`
✅ Maintains backward compatibility with company research

## Example Usage

### Company Research (existing)
```python
company_context = CompanyContext(
    name="Apple Inc.",
    business_areas=["Consumer Electronics"],
    current_status={}
)

topics = await topic_agent.extract_topics(search_results, company_context, iteration=1)
# Returns: ["Apple AI Strategy", "iPhone 15 Production", ...]
```

### Macro Research (new)
```python
from deep_news_agent.agents.macro_interfaces import get_macro_context, MacroCategory

macro_context = get_macro_context(MacroCategory.MONETARY_POLICY)

topics = await topic_agent.extract_topics(search_results, macro_context, iteration=1)
# Returns: ["Federal Reserve Rate Policy Outlook", "Market Implications of Fed Tightening", ...]
```

## Next Step

✅ SearchAgent - Updated
✅ TopicAgent - Updated
⏳ OrchestratorAgent - In Progress
