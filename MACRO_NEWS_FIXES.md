# Macro News Implementation - Fixes Applied

## Issues Fixed

### 1. Database Storage Bug ✅
**Problem**: Topics were being extracted but not saved to Supabase
**Root Cause**: `TopicAgent` and `RankingAgent` were initialized without `db_manager` parameter
**Fix**: Updated [run_macro_research.py:78-80](deep_news_agent/run_macro_research.py#L78-80) to pass `db_manager` to agents

### 2. Aggressive Topic Merging ✅
**Problem**: Too many similar Fed topics (e.g., "Fed Rate Cuts", "Fed Forward Guidance") not being merged
**Root Cause**: Merge criteria was designed for company research, too conservative for macro topics
**Fix**: Created macro-specific merge prompt in [topic_agent.py:360-403](deep_news_agent/agents/topic_agent.py#L360-403)
- Lowered semantic overlap threshold from 70% to 40%
- Added aggressive consolidation rule: "When in doubt → MERGE"
- Target: 5-8 consolidated topics per category instead of 20 fragmented ones

### 3. Topic Diversity Issue 🔍
**Problem**: All topics are Fed-focused, missing geopolitics and domestic politics
**Root Cause**: Only ran `monetary_policy` category
**Solution**: Run research for ALL 8 categories to get diverse topics

## Available Macro Categories

The system has 8 predefined macro/political categories:

### Economic/Macro Categories
1. **`monetary_policy`** - Federal Reserve & Monetary Policy
   - Interest rates, Fed guidance, QE/QT, central bank policy

2. **`fiscal_policy`** - Government Spending & Fiscal Policy
   - Budget proposals, infrastructure, tax policy, stimulus, debt ceiling

3. **`inflation_economy`** - Inflation & Economic Indicators
   - CPI, employment, GDP, consumer spending, manufacturing

4. **`trade_policy`** - Trade Policy & Tariffs
   - Tariffs, trade agreements, export/import restrictions, supply chain

5. **`energy_commodities`** - Energy Markets & Commodities
   - Oil/gas prices, OPEC, energy transition, commodity volatility

6. **`regulation`** - Financial Regulation & Policy
   - Banking regulation, SEC enforcement, antitrust, crypto regulation

### Political Categories
7. **`geopolitics`** - Geopolitical Events & International Relations
   - International conflicts, sanctions, military actions, alliances

8. **`elections_politics`** - Elections & Political Developments
   - Elections, policy proposals, polling, legislative battles

## How to Run Macro Research

### Run All Categories (Recommended for Full Coverage)
```bash
source venv/bin/activate
python deep_news_agent/run_macro_research.py --iterations 2
```
This will research all 8 categories and give you diverse topics across economy, politics, and geopolitics.

### Run Specific Categories
```bash
# Geopolitics (get China, Russia, Middle East tensions)
python deep_news_agent/run_macro_research.py --category geopolitics --iterations 2

# Elections & Politics (get domestic US politics)
python deep_news_agent/run_macro_research.py --category elections_politics --iterations 2

# Energy (get oil, OPEC, energy transition)
python deep_news_agent/run_macro_research.py --category energy_commodities --iterations 2
```

### Run Multiple Specific Categories
Run them sequentially:
```bash
source venv/bin/activate
python deep_news_agent/run_macro_research.py --category geopolitics --iterations 2
python deep_news_agent/run_macro_research.py --category elections_politics --iterations 2
python deep_news_agent/run_macro_research.py --category fiscal_policy --iterations 2
```

## Expected Results

After running all categories, you should see in Supabase `topics` table:

### Federal Reserve & Monetary Policy (monetary_policy)
- 3-5 consolidated topics about Fed policy, rate decisions, inflation targeting

### Geopolitical Events (geopolitics)
- 3-5 topics about China-US tensions, Middle East conflicts, Russia-Ukraine, etc.

### Elections & Politics (elections_politics)
- 3-5 topics about 2024 election, campaign developments, policy proposals, polls

### Trade Policy (trade_policy)
- 3-5 topics about tariffs, trade agreements, China trade, supply chain

### Inflation & Economy (inflation_economy)
- 3-5 topics about CPI, jobs data, recession indicators, consumer spending

### Energy & Commodities (energy_commodities)
- 3-5 topics about oil prices, OPEC, energy transition, commodity markets

### Financial Regulation (regulation)
- 3-5 topics about banking rules, SEC actions, crypto regulation, antitrust

### Fiscal Policy (fiscal_policy)
- 3-5 topics about budget, infrastructure, tax policy, debt ceiling

## Database Schema

Topics are stored with:
```sql
company_id = NULL  -- Macro topics have no company
topic_type = 'macro' or 'political'
sector = 'Monetary Policy', 'Geopolitics', 'Elections', etc.
```

## Frontend Integration

Topics will appear via:
- `/api/macro-topics?topic_type=macro` - Economic/market topics
- `/api/macro-topics?topic_type=political` - Political topics
- `/api/front-page-topics` - Combined macro + company topics

## Viewing Results

Check topics in database:
```bash
source venv/bin/activate
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get macro topics grouped by sector
result = supabase.table('topics').select('*').is_('company_id', 'null').execute()
topics_by_sector = {}
for topic in result.data:
    sector = topic.get('sector', 'Unknown')
    if sector not in topics_by_sector:
        topics_by_sector[sector] = []
    topics_by_sector[sector].append(topic['name'])

for sector, topics in topics_by_sector.items():
    print(f'\n{sector} ({len(topics)} topics):')
    for topic in topics[:5]:
        print(f'  - {topic}')
"
```

## Next Steps

1. **Run all categories** to populate diverse topics:
   ```bash
   source venv/bin/activate
   python deep_news_agent/run_macro_research.py --iterations 2
   ```

2. **Verify diversity** in Supabase - should see topics across all 8 sectors

3. **Test frontend** - macro topics should appear in "Market Overview" section

4. **Schedule regular updates** - Run daily/weekly to keep topics fresh
