# OrchestratorAgent Updates - Unified Context Support

## Changes Made

### 1. **Imports Updated**
- ✅ Added `ResearchContext, ResearchType` to imports from interfaces

### 2. **Main Pipeline Method Updated**
```python
async def run_pipeline(self, context: ResearchContext) -> List[RankedTopic]:
```

Now accepts unified `ResearchContext` instead of `CompanyContext`

### 3. **Database Initialization - Conditional Logic**
```python
# Initialize database if available (only for companies)
if self.db_manager and context.get_research_type() == ResearchType.COMPANY:
    self.company_id = self.db_manager.create_or_get_company(context)
    self.logger.info(f"Database integration enabled - Company ID: {self.company_id}")
else:
    self.company_id = None  # Macro topics don't have company_id
```

**Key Point**: Macro topics DON'T get a company_id since they're stored with `company_id = NULL`

### 4. **Adaptive Initial Questions Generation**

The `_generate_initial_questions()` method now branches based on research type:

#### For Company Research:
```python
def _generate_company_questions(self, context: ResearchContext) -> List[Question]:
    # Business area questions
    for business_area in context.get_focus_areas()[:5]:
        "What are the latest developments in {business_area} for {company}?"

    # Market position question
    "How is {company} positioned in the market?"

    # Recent news
    "What are the latest breaking news about {company}?"

    # Geopolitical context
    "How do geopolitical factors affect {company}?"

    # Business growth
    "What are {company}'s growth strategies?"

    # Leadership changes
    "Are there any leadership changes at {company}?"
```

#### For Macro/Political Research:
```python
def _generate_macro_questions(self, context: ResearchContext) -> List[Question]:
    # Focus area questions (market-wide)
    for focus_area in context.get_focus_areas()[:5]:
        "What are the latest developments in {focus_area} and their market implications?"

    # Market impact
    "How is {category} affecting investor sentiment and market positioning?"

    # Recent policy changes
    "What are the most recent policy changes related to {category}?"

    # Analyst outlook
    "What is the current market outlook and analyst consensus on {category}?"
```

### 5. **Key Differences: Company vs Macro Questions**

| Aspect | Company Questions | Macro Questions |
|--------|------------------|-----------------|
| **Focus** | Company operations, products, strategy | Market implications, investor sentiment |
| **Examples** | "Apple's AI strategy developments" | "Fed policy impact on markets" |
| **Business Areas** | "Consumer Electronics developments for Apple" | "Interest rate developments and market implications" |
| **Recent News** | "Latest breaking news about Apple" | "Most recent policy changes related to Fed Policy" |
| **Context** | "Geopolitical factors affecting Apple" | "Market outlook and analyst consensus on Fed Policy" |

### 6. **Pipeline State**
PipelineState still uses `company_context` field name for backward compatibility:
```python
self.current_state = PipelineState(
    company_context=context,  # Works with both CompanyContext and MarketContext
    ...
)
```

### 7. **Status Reporting Updated**
```python
def get_pipeline_status(self):
    return {
        "research_target": self.current_state.company_context.get_display_name(),
        # Returns "Apple Inc." or "Federal Reserve & Monetary Policy"
        ...
    }
```

## Complete Pipeline Flow

### Company Research Pipeline:
1. **Initial Questions**: Business areas, market position, leadership
2. **Iteration 1**: Tavily search + Earnings transcripts
3. **Topic Extraction**: Company-specific topics ("Apple AI Strategy")
4. **Iterations 2-5**: Tavily only, refine topics
5. **Final Ranking**: Rank by company impact

### Macro Research Pipeline:
1. **Initial Questions**: Market implications, policy changes, analyst outlook
2. **Iteration 1**: Tavily search only (NO earnings)
3. **Topic Extraction**: Market-wide topics ("Fed Policy Shift")
4. **Iterations 2-5**: Tavily only, refine topics
5. **Final Ranking**: Rank by market impact

## Verification

✅ No unhandled `company_context` parameter references
✅ All methods use `context: ResearchContext`
✅ Adaptive question generation based on `context.get_research_type()`
✅ Conditional database logic (company_id only for companies)
✅ Maintains backward compatibility

## Example Usage

### Company Research
```python
company_context = CompanyContext(
    name="Apple Inc.",
    business_areas=["Consumer Electronics"],
    current_status={},
    ticker="AAPL"
)

orchestrator = OrchestratorAgent(...)
ranked_topics = await orchestrator.run_pipeline(company_context)
# Returns: [RankedTopic("Apple AI Strategy", score=0.95), ...]
```

### Macro Research
```python
from deep_news_agent.agents.macro_interfaces import get_macro_context, MacroCategory

macro_context = get_macro_context(MacroCategory.MONETARY_POLICY)

orchestrator = OrchestratorAgent(...)
ranked_topics = await orchestrator.run_pipeline(macro_context)
# Returns: [RankedTopic("Fed Rate Policy Outlook", score=0.92), ...]
```

## Agent Update Status

✅ **SearchAgent** - Updated with adaptive prompts
✅ **TopicAgent** - Updated with adaptive prompts
✅ **OrchestratorAgent** - Updated with adaptive questions
⏳ **Database Migration** - Next step
⏳ **Backend Service** - Next step
⏳ **Frontend Integration** - Next step
