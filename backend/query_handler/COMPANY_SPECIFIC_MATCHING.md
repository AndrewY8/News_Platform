# Company-Specific Topic Matching

## Overview

The Intelligent Query System ensures that **topic matching is company-specific**, preventing cross-contamination between different companies' topics.

**Problem Solved:** "Tesla earnings" will NEVER match "Microsoft earnings"

---

## How It Works

### **Query Flow with Company Filtering**

```
User Query: "Tesla Q4 earnings"
         ↓
┌────────────────────────────────────┐
│ STEP 1: Extract Company & Topics  │
├────────────────────────────────────┤
│ Company: "Tesla"                   │
│ Topics: ["earnings", "Q4"]         │
└────────────────┬───────────────────┘
                 ↓
┌────────────────────────────────────┐
│ STEP 2: Get Company ID             │
├────────────────────────────────────┤
│ Query: companies WHERE name='Tesla'│
│ Result: company_id = 100           │
└────────────────┬───────────────────┘
                 ↓
┌────────────────────────────────────┐
│ STEP 3: Filter Topics by Company  │
├────────────────────────────────────┤
│ Query: topics WHERE company_id=100│
│ Result: ONLY Tesla's topics        │
│   - Tesla Q4 Earnings (id=1)       │
│   - Tesla Cybertruck (id=2)        │
│                                    │
│ NEVER returns:                     │
│   ❌ Microsoft Q4 Earnings (id=3)  │
│   ❌ Apple Q4 Earnings (id=4)      │
└────────────────┬───────────────────┘
                 ↓
┌────────────────────────────────────┐
│ STEP 4: Match Query to Filtered   │
├────────────────────────────────────┤
│ Input: ["earnings", "Q4"]          │
│ Search in: Tesla's topics ONLY     │
│ Match: "Tesla Q4 Earnings" ✅      │
└────────────────────────────────────┘
```

---

## Code Implementation

### **Key Protection Point**

**File:** `intelligent_query_router.py:302-341`

```python
def _get_company_topics(self, company: str) -> List[Dict[str, Any]]:
    """
    Get existing topics for a company from database
    CRITICAL: Only returns topics for the specified company
    """
    # Step 1: Get company ID
    company_result = self.research_db.supabase.table("companies")
        .select("id, name")
        .eq("name", company)  # ← Filter by company name
        .execute()

    company_id = company_result.data[0]['id']

    # Step 2: Get ONLY this company's topics
    topics_result = self.research_db.supabase.table("topics")
        .select("id, name, description, ...")
        .eq("company_id", company_id)  # ← CRITICAL FILTER
        .execute()

    # Returns ONLY topics where company_id matches
    return topics_result.data
```

**The magic line:**
```python
.eq("company_id", company_id)  # Line 339
```

This ensures the topic list is **pre-filtered** before semantic matching occurs.

---

## Test Case Demonstration

### **Test 1: Tesla Earnings Query**

```python
# User query
"Tesla Q4 earnings"

# Step 1: Extract
company = "Tesla"
topics = ["earnings", "Q4"]

# Step 2: Get company ID
company_id = 100  # Tesla's ID

# Step 3: Get Tesla's topics ONLY
tesla_topics = [
    {"id": 1, "name": "Q4 2024 Earnings Report", "company_id": 100},
    {"id": 2, "name": "Cybertruck Production", "company_id": 100}
]

# Step 4: Match
matched = "Q4 2024 Earnings Report"  # ✅ Tesla's earnings
```

### **Test 2: Microsoft Earnings Query**

```python
# User query
"Microsoft Q4 earnings"

# Step 1: Extract
company = "Microsoft"
topics = ["earnings", "Q4"]

# Step 2: Get company ID
company_id = 200  # Microsoft's ID

# Step 3: Get Microsoft's topics ONLY
microsoft_topics = [
    {"id": 3, "name": "Q4 2024 Earnings Report", "company_id": 200},
    {"id": 4, "name": "Azure Cloud Growth", "company_id": 200}
]

# Step 4: Match
matched = "Q4 2024 Earnings Report"  # ✅ Microsoft's earnings
```

**Result:** Even though both companies have "Q4 2024 Earnings Report", the system correctly matches each query to its respective company!

---

## Database Schema

### **Companies Table**
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    business_areas TEXT[],
    created_at TIMESTAMP
);

-- Example data
INSERT INTO companies (id, name) VALUES
    (100, 'Tesla'),
    (200, 'Microsoft'),
    (300, 'Apple');
```

### **Topics Table**
```sql
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),  -- ← Foreign key
    name VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP
);

-- Example data
INSERT INTO topics (id, company_id, name) VALUES
    (1, 100, 'Q4 2024 Earnings Report'),  -- Tesla
    (2, 100, 'Cybertruck Production'),    -- Tesla
    (3, 200, 'Q4 2024 Earnings Report'),  -- Microsoft
    (4, 200, 'Azure Cloud Growth');       -- Microsoft
```

**Key Point:** The `company_id` foreign key ensures referential integrity.

---

## Why This Matters

### **Without Company Filtering (Bad)**

```python
# BAD: Get ALL topics from all companies
all_topics = get_all_topics()  # Returns topics from ALL companies

# Query: "Tesla earnings"
query_topics = ["earnings", "Q4"]

# Match against ALL topics
matched = match_topics(query_topics, all_topics)

# Problem: Could match ANY company's earnings!
# Result: "Microsoft Q4 Earnings" (similarity: 0.85) ❌
# Expected: "Tesla Q4 Earnings" (similarity: 0.82) ✅
```

**Issue:** First match wins, regardless of company!

### **With Company Filtering (Good)**

```python
# GOOD: Get topics for specific company only
company = "Tesla"
company_id = get_company_id(company)  # Returns 100
tesla_topics = get_topics_for_company(company_id)  # Only Tesla's topics

# Query: "Tesla earnings"
query_topics = ["earnings", "Q4"]

# Match against ONLY Tesla's topics
matched = match_topics(query_topics, tesla_topics)

# Result: "Tesla Q4 Earnings" ✅
# Never sees: Microsoft, Apple, or any other company's topics
```

**Benefit:** Guaranteed correct company match!

---

## Validation in Logs

When the system runs, look for these log messages:

```
INFO: Target company: Tesla
INFO: Found 2 existing topics for Tesla
DEBUG: Company topics: ['Q4 2024 Earnings Report', 'Cybertruck Production']
INFO: ✅ Cache hit! Company: Tesla, Topic: Q4 2024 Earnings Report
```

**Key indicators:**
1. `Target company: Tesla` - Company identified
2. `Found X topics for Tesla` - Filtered by company
3. `Company: Tesla, Topic: ...` - Match confirmed for correct company

---

## Edge Cases Handled

### **1. Company Not in Database**

```python
# Query: "Unknown Startup earnings"
company = "Unknown Startup"

# Get company ID
company_result = query_companies(company)
# Returns: [] (empty)

# Result: Return "fresh_search_needed"
# Never tries to match against other companies' topics
```

### **2. Ticker → Company Name Mapping**

```python
# Query: "TSLA earnings"
company = "TSLA"  # Ticker symbol

# Lookup mapping
ticker_to_name = {'TSLA': 'Tesla', 'MSFT': 'Microsoft', ...}
company_name = ticker_to_name.get("TSLA")  # "Tesla"

# Get topics for Tesla
topics = get_topics_for_company("Tesla")  # ✅ Correct company
```

### **3. Similar Topic Names Across Companies**

```python
# Database has:
# - Tesla: "Q4 Earnings Report"
# - Microsoft: "Q4 Earnings Report"
# - Apple: "Q4 Earnings Report"

# Query: "Microsoft earnings"
company = "Microsoft"

# Get Microsoft's topics ONLY
topics = get_topics_for_company("Microsoft")
# Returns: ONLY Microsoft's "Q4 Earnings Report"

# Never sees Tesla's or Apple's earnings topics!
```

---

## Testing

### **Run Company-Specific Test**

```bash
cd backend
python query_handler/test_company_specific_matching.py
```

**Expected Output:**
```
✅ CORRECT: Matched Tesla's earnings topic (company_id: 100)
✅ CORRECT: Matched Microsoft's earnings topic (company_id: 200)
✅ All company-specific matching tests demonstrate correct behavior!
```

### **Run Full Integration Test**

```bash
cd backend
python query_handler/test_intelligent_query.py
```

Look for:
```
INFO: Target company: Tesla
INFO: Found 2 existing topics for Tesla
✅ Cache hit! Company: Tesla, Topic: Q4 2024 Earnings Report
```

---

## Summary

### **How Company-Specific Matching is Guaranteed**

1. ✅ **Extract company first** from query
2. ✅ **Get company_id** from database
3. ✅ **Filter topics** by `company_id` (SQL WHERE clause)
4. ✅ **Match only within** filtered topic list
5. ✅ **Return result** with company verification

### **Key Protection**

```python
# Line 339 in intelligent_query_router.py
.eq("company_id", company_id)
```

This single line ensures:
- "Tesla earnings" only sees Tesla topics
- "Microsoft earnings" only sees Microsoft topics
- No cross-contamination between companies
- Correct matching every time

### **Result**

**"Tesla Q4 earnings" will NEVER match "Microsoft Q4 earnings"** ✅

The company is extracted first, topics are filtered by company_id, and matching happens only within that company's topic space.
