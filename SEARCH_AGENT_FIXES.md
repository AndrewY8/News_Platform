# SearchAgent Fixes - Unified Context Support

## Issues Fixed

### 1. **Type Annotation Errors**
- ❌ Before: `context: 'ResearchContext'` (string, not type)
- ✅ After: `context: ResearchContext` (proper type)

### 2. **Missing Imports**
- ❌ Before: `ResearchContext` not imported
- ✅ After: Added `from .interfaces import ResearchContext, CompanyContext, Question as InterfaceQuestion`

### 3. **Duplicate Definitions**
- ❌ Before: `CompanyContext` and `Question` defined locally in search_agent.py
- ✅ After: Removed local definitions, use from interfaces.py

### 4. **Inconsistent Parameter Names**
- ❌ Before: Mix of `company_context: CompanyContext` and `context: ResearchContext`
- ✅ After: All methods use `context: ResearchContext`

## Methods Updated

All methods now accept unified `ResearchContext`:

1. ✅ `initial_search(context: ResearchContext, ...)`
2. ✅ `subsequent_search(context: ResearchContext, ...)`
3. ✅ `generate_search_queries(questions, context: ResearchContext)`
4. ✅ `search_with_tavily(queries, context: ResearchContext)`
5. ✅ `search_earnings_transcripts(context: ResearchContext)`
6. ✅ `filter_and_rank_results(results, context: ResearchContext)`
7. ✅ `generate_questions_from_topics(topics, context: ResearchContext, iteration)`
8. ✅ `_build_query_generation_prompt(questions, context: ResearchContext)`
9. ✅ `_build_question_generation_prompt(topics, context: ResearchContext, iteration)`

## Key Behavioral Changes

### 1. **Adaptive Earnings Search**
```python
# Only search earnings if context supports it
earnings_results = []
if context.should_use_earnings():  # True for companies, False for macro
    earnings_results = await self.search_earnings_transcripts(context)
```

### 2. **Context-Aware Prompts**
The `_build_query_generation_prompt` method now generates **different prompts** based on research type:

**For Company Research:**
```
Company: Apple Inc.
Business Areas: Consumer Electronics, Software

Convert these questions into company-specific search queries...
- Include company name + relevant keywords
- Focus on earnings, products, business developments

Examples:
- Good: "Apple 2024 earnings revenue growth"
```

**For Macro Research:**
```
Macro Research Category: Federal Reserve & Monetary Policy
Focus Areas: Interest rates, Fed communications

Convert these questions into MARKET-WIDE macro search queries...
- Focus on MARKET IMPLICATIONS and investor impact
- Use financial/economic terminology (Fed, rates, inflation)
- NO company-specific focus

Examples:
- Good: "Federal Reserve 2024 interest rate policy market outlook"
```

### 3. **Universal Context Methods**
All methods now use `context.get_display_name()` instead of `context.name`:

```python
company_name = context.get_display_name()  # "Apple Inc." or "Federal Reserve Policy"
keywords = context.get_search_keywords()   # ["Apple", "AAPL"] or ["Fed", "rates"]
focus_areas = context.get_focus_areas()    # Business areas or macro focus areas
```

## Verification

No more `company_context` references:
```bash
grep -n "company_context" search_agent.py
# Only in commented-out TODO sections
```

## Next Steps

1. ✅ SearchAgent fully updated
2. ⏳ Update TopicAgent with adaptive prompts
3. ⏳ Update OrchestratorAgent to use ResearchContext
4. ⏳ Database migration
5. ⏳ Create macro research service
