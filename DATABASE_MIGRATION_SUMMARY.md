# Database Migration Summary - Macro Topic Support

## ✅ Migration Complete

### Files Created/Modified:

1. **`deep_news_agent/db/migrations/001_add_macro_support.sql`** - Database migration script
2. **`deep_news_agent/db/research_db_manager.py`** - Added macro topic methods

---

## Database Schema Changes

### 1. **Topics Table - Modified**

**Changes:**
- `company_id` → Now NULLABLE (allows macro topics)
- Added `topic_type` → VARCHAR(50) with values: `'company_specific'`, `'macro'`, `'political'`
- Added `sector` → VARCHAR(100) for market sectors

**Before:**
```sql
company_id INTEGER REFERENCES companies(id) NOT NULL
```

**After:**
```sql
company_id INTEGER REFERENCES companies(id),  -- NULL for macro topics
topic_type VARCHAR(50) DEFAULT 'company_specific',
sector VARCHAR(100)
```

### 2. **New Indexes**
```sql
CREATE INDEX idx_topics_topic_type ON topics(topic_type);
CREATE INDEX idx_topics_sector ON topics(sector);
CREATE INDEX idx_topics_company_id_null ON topics(company_id) WHERE company_id IS NULL;
```

### 3. **New Views**

#### `macro_political_topics`
All macro/political topics (company_id IS NULL) with article counts

#### `macro_topics_recent`
Macro/political topics from last 24 hours

#### `front_page_topics`
**Combined view** - Top 10 company topics + Top 10 macro topics

```sql
SELECT * FROM front_page_topics LIMIT 20;
```

Returns mixed company and macro topics ordered by final_score

### 4. **New Database Function**

```sql
get_topics_by_type(topic_type, limit, hours_back)
```

**Usage:**
```sql
-- Get recent macro topics
SELECT * FROM get_topics_by_type('macro', 10, 24);

-- Get political topics
SELECT * FROM get_topics_by_type('political', 5, 48);
```

---

## ResearchDBManager New Methods

### 1. **`store_macro_topic()`**
```python
stored_topic = db_manager.store_macro_topic(
    topic=topic,
    topic_type='macro',  # or 'political'
    sector='Monetary Policy',
    iteration=1
)
```

Stores topic with:
- `company_id = NULL`
- `topic_type = 'macro'` or `'political'`
- `sector` for categorization

### 2. **`get_macro_topics()`**
```python
macro_topics = db_manager.get_macro_topics(
    topic_type='macro',
    limit=10,
    hours_back=24
)
```

Returns recent macro topics with article counts

### 3. **`get_front_page_topics()`**
```python
front_page = db_manager.get_front_page_topics(limit=20)
```

Returns combined company + macro topics for front page display

---

## Data Examples

### Company Topic (existing)
```json
{
  "id": 1,
  "company_id": 5,
  "topic_type": "company_specific",
  "sector": null,
  "name": "Apple AI Strategy Expansion",
  "description": "Apple expanding AI capabilities...",
  "business_impact": "Could increase services revenue...",
  "urgency": "high",
  "final_score": 0.92
}
```

### Macro Topic (new)
```json
{
  "id": 2,
  "company_id": null,
  "topic_type": "macro",
  "sector": "Monetary Policy",
  "name": "Federal Reserve Rate Policy Shift",
  "description": "Fed signals potential rate cuts...",
  "business_impact": "Market-wide impact on equity valuations...",
  "urgency": "high",
  "final_score": 0.88
}
```

### Political Topic (new)
```json
{
  "id": 3,
  "company_id": null,
  "topic_type": "political",
  "sector": "Elections",
  "name": "2024 Election Market Implications",
  "description": "Presidential election policy proposals...",
  "business_impact": "Potential regulatory changes affecting sectors...",
  "urgency": "medium",
  "final_score": 0.75
}
```

---

## Migration Steps to Run

1. **Connect to Supabase**
```bash
# Get Supabase connection details from .env
```

2. **Run Migration Script**
```sql
-- In Supabase SQL Editor, execute:
/deep_news_agent/db/migrations/001_add_macro_support.sql
```

3. **Verify Migration**
```sql
-- Check topics table structure
\d topics

-- Verify views exist
SELECT * FROM macro_political_topics LIMIT 5;
SELECT * FROM front_page_topics LIMIT 20;

-- Test function
SELECT * FROM get_topics_by_type('macro', 10, 24);
```

---

## Usage in Pipeline

### Storing Macro Topics
```python
from deep_news_agent.agents.macro_interfaces import get_macro_context, MacroCategory
from deep_news_agent.db.research_db_manager import ResearchDBManager

# Initialize
db_manager = ResearchDBManager(supabase_url, supabase_key)

# Get macro context
macro_context = get_macro_context(MacroCategory.MONETARY_POLICY)

# Run pipeline
orchestrator = OrchestratorAgent(...)
ranked_topics = await orchestrator.run_pipeline(macro_context)

# Topics are automatically stored with company_id=NULL
# Store happens in TopicAgent.extract_topics() when company_id is None
```

### Retrieving Macro Topics
```python
# Get recent macro topics
macro_topics = db_manager.get_macro_topics(topic_type='macro', limit=10)

# Get political topics
political_topics = db_manager.get_macro_topics(topic_type='political', limit=10)

# Get front page (mixed)
front_page = db_manager.get_front_page_topics(limit=20)
```

---

## Next Steps

✅ Database migration created
✅ ResearchDBManager updated with macro methods
⏳ Create backend service to run macro research
⏳ Create API endpoints
⏳ Update frontend to display macro topics
