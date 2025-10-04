# Macro News Implementation - Unified Agent Approach

## Overview

We're extending the Deep Research Agent infrastructure to support **macro/political news** while reusing the existing agent codebase. This is accomplished through a **unified `ResearchContext` interface** that both company and macro research implement.

## Key Design Decision: Unified vs Separate Agents

**CHOSEN APPROACH: Unified Agents** ✅

Instead of creating separate `MacroSearchAgent`, `MacroTopicAgent`, etc., we modify the existing agents to work with BOTH company and macro contexts using a common interface.

### Why Unified is Better:

| Aspect | Separate Agents ❌ | Unified Agents ✅ |
|--------|-------------------|------------------|
| **Code Duplication** | High (duplicate search/topic/orchestrator logic) | Low (reuse existing logic) |
| **Maintenance** | 2x agents to maintain | Single agent codebase |
| **Bug Fixes** | Must fix in 2 places | Fix once, applies to both |
| **Feature Additions** | Add to both agents | Add once |
| **Testing** | Test company AND macro versions | Test unified interface |

## Architecture

### 1. Unified ResearchContext Interface

```python
class ResearchContext(ABC):
    """Base class for all research contexts"""

    @abstractmethod
    def get_research_type(self) -> ResearchType:  # COMPANY, MACRO, POLITICAL
        pass

    @abstractmethod
    def get_display_name(self) -> str:  # "Apple" or "Federal Reserve Policy"
        pass

    @abstractmethod
    def get_search_keywords(self) -> List[str]:  # ["Apple", "AAPL"] or ["Fed", "interest rates"]
        pass

    @abstractmethod
    def get_focus_areas(self) -> List[str]:  # Business areas or macro focus areas
        pass

    @abstractmethod
    def should_use_earnings(self) -> bool:  # True for companies, False for macro
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass
```

### 2. Two Implementations

**CompanyContext** (existing, now implements ResearchContext):
```python
@dataclass
class CompanyContext(ResearchContext):
    name: str  # "Apple Inc."
    business_areas: List[str]  # ["Consumer Electronics", "Software"]
    current_status: Dict[str, Any]
    ticker: Optional[str] = None

    def should_use_earnings(self) -> bool:
        return True  # Companies use earnings transcripts
```

**MarketContext** (new, implements ResearchContext):
```python
@dataclass
class MarketContext(ResearchContext):
    category: MacroCategory  # MONETARY_POLICY, INFLATION, ELECTIONS
    topic_type: str  # "macro" or "political"
    focus_areas: List[str]  # ["Interest rates", "Fed communications"]
    display_name: str  # "Federal Reserve & Monetary Policy"

    def should_use_earnings(self) -> bool:
        return False  # Macro doesn't use earnings
```

### 3. Modified Agents

**SearchAgent** (modified to accept ResearchContext):
```python
async def initial_search(self, context: ResearchContext, questions: List[Question]):
    """
    Performs initial search

    For companies: Tavily + Earnings
    For macro: Tavily only
    """
    tavily_results = await self.search_with_tavily(search_queries, context)

    # Only search earnings if context supports it
    earnings_results = []
    if context.should_use_earnings():  # ← Key check
        earnings_results = await self.search_earnings_transcripts(context)

    return tavily_results + earnings_results
```

**TopicAgent** (will be modified):
- Accept `ResearchContext` instead of `CompanyContext`
- Adapt prompts based on `context.get_research_type()`
- For macro: Use market-focused prompt (no company-specific language)
- For company: Use existing company-focused prompt

**OrchestratorAgent** (will be modified):
- Accept `ResearchContext` instead of `CompanyContext`
- Generate initial questions based on context type:
  - Company: Questions about business areas
  - Macro: Questions about market themes

## Implementation Progress

### ✅ Completed

1. **ResearchContext Interface** - Created in `interfaces.py`
2. **CompanyContext Updated** - Now implements ResearchContext
3. **MarketContext Created** - Implements ResearchContext with predefined categories
4. **SearchAgent Modified** - `initial_search()` and `subsequent_search()` now use ResearchContext

### 🔄 In Progress

1. **SearchAgent** - Updating remaining methods to use ResearchContext

### ⏳ To Do

1. **TopicAgent** - Modify to use ResearchContext with adaptive prompts
2. **OrchestratorAgent** - Modify to use ResearchContext
3. **Database Migration** - Add nullable `company_id`, `topic_type` field
4. **Macro Service** - Backend service to run macro research
5. **API Routes** - `/api/macro-topics` endpoint
6. **Frontend** - Market Overview section

## Predefined Macro Categories

We've created 8 predefined macro categories:

1. **MONETARY_POLICY** - Fed policy, interest rates, FOMC
2. **INFLATION** - CPI, PCE, price pressures
3. **EMPLOYMENT** - Jobs reports, unemployment, wages
4. **FISCAL_POLICY** - Government spending, debt ceiling
5. **ELECTIONS** - Political developments, policy proposals
6. **GEOPOLITICS** - Trade relations, conflicts, sanctions
7. **ECONOMIC_INDICATORS** - GDP, recession indicators
8. **TRADE_POLICY** - Tariffs, trade agreements

Each category has:
- Predefined focus areas
- Default search keywords
- Current status tracking (e.g., fed funds rate)

## Database Schema

### Modified `topics` Table

```sql
-- Make company_id nullable (for macro topics)
ALTER TABLE topics ALTER COLUMN company_id DROP NOT NULL;

-- Add topic_type field
ALTER TABLE topics ADD COLUMN topic_type VARCHAR(50) DEFAULT 'company_specific'
CHECK (topic_type IN ('company_specific', 'macro', 'political'));

-- Add sector field (for market-wide topics)
ALTER TABLE topics ADD COLUMN sector VARCHAR(100);

-- Indexes
CREATE INDEX idx_topics_topic_type ON topics(topic_type);
CREATE INDEX idx_topics_sector ON topics(sector);
```

### Views

```sql
-- Get recent macro/political topics
CREATE VIEW macro_topics_latest AS
SELECT
    t.*,
    COUNT(at.article_id) as article_count
FROM topics t
LEFT JOIN article_topics at ON t.id = at.topic_id
WHERE t.company_id IS NULL  -- Macro topics have no company
  AND t.topic_type IN ('macro', 'political')
  AND t.extraction_date > NOW() - INTERVAL '24 hours'
GROUP BY t.id
ORDER BY t.final_score DESC;
```

## Usage Example

### Running Company Research (existing)
```python
company_context = CompanyContext(
    name="Apple Inc.",
    business_areas=["Consumer Electronics", "Software"],
    current_status={},
    ticker="AAPL"
)

orchestrator = OrchestratorAgent(...)
topics = await orchestrator.run_pipeline(company_context)
```

### Running Macro Research (new)
```python
from deep_news_agent.agents.macro_interfaces import get_macro_context, MacroCategory

# Get predefined macro context
macro_context = get_macro_context(MacroCategory.MONETARY_POLICY)

# Use SAME orchestrator
orchestrator = OrchestratorAgent(...)
topics = await orchestrator.run_pipeline(macro_context)

# Topics are stored with company_id = NULL, topic_type = 'macro'
```

## Key Differences: Company vs Macro Research

| Aspect | Company Research | Macro Research |
|--------|-----------------|---------------|
| **Context Type** | CompanyContext | MarketContext |
| **Earnings Search** | ✅ Yes | ❌ No |
| **Search Keywords** | Company name, ticker | Macro keywords (Fed, inflation) |
| **Initial Questions** | Based on business areas | Based on macro focus areas |
| **Topic Extraction Prompt** | "impact on [Company]" | "market-wide impact" |
| **Database Storage** | `company_id` = company ID | `company_id` = NULL |
| **topic_type** | "company_specific" | "macro" or "political" |

## Next Steps

1. Complete SearchAgent modification (all methods use ResearchContext)
2. Modify TopicAgent with adaptive prompts
3. Modify OrchestratorAgent for unified context
4. Run database migration
5. Create macro research service
6. Add API endpoints
7. Update frontend with Market Overview section

## Files Modified/Created

### Created:
- `deep_news_agent/agents/macro_interfaces.py` - MarketContext and predefined categories
- `deep_news_agent/agents/macro_search_agent.py` - (Can be deleted, using unified approach)
- `MACRO_NEWS_IMPLEMENTATION.md` - This file

### Modified:
- `deep_news_agent/agents/interfaces.py` - Added ResearchContext, updated CompanyContext
- `deep_news_agent/agents/search_agent.py` - Updated to use ResearchContext (in progress)

### To Modify:
- `deep_news_agent/agents/topic_agent.py`
- `deep_news_agent/agents/orchestrator_agent.py`
- `deep_news_agent/db/research_db_manager.py`
- Backend API files
- Frontend files
