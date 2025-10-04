-- Migration: Add Macro/Political News Support
-- Date: 2025-01-04
-- Description: Extends topics table to support macro/political topics without company association

-- Step 1: Drop dependent views first (we'll recreate them later)
DROP VIEW IF EXISTS company_topic_summary CASCADE;
DROP VIEW IF EXISTS front_page_topics CASCADE;
DROP VIEW IF EXISTS macro_topics_recent CASCADE;
DROP VIEW IF EXISTS macro_political_topics CASCADE;

-- Step 2: Make company_id nullable (allow topics without companies)
ALTER TABLE topics
ALTER COLUMN company_id DROP NOT NULL;

-- Step 3: Add topic_type field to differentiate news categories
ALTER TABLE topics
ADD COLUMN IF NOT EXISTS topic_type VARCHAR(50) DEFAULT 'company_specific';

-- Add constraint separately if column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'topics_topic_type_check'
    ) THEN
        ALTER TABLE topics
        ADD CONSTRAINT topics_topic_type_check
        CHECK (topic_type IN ('company_specific', 'macro', 'political'));
    END IF;
END $$;

-- Step 4: Add sector field for market-wide topics
ALTER TABLE topics
ADD COLUMN IF NOT EXISTS sector VARCHAR(100);

-- Step 5: Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_topics_topic_type ON topics(topic_type);
CREATE INDEX IF NOT EXISTS idx_topics_sector ON topics(sector);
CREATE INDEX IF NOT EXISTS idx_topics_company_id_null ON topics(company_id) WHERE company_id IS NULL;

-- Step 6: Create view for macro/political topics
CREATE VIEW macro_political_topics AS
SELECT
    t.id,
    t.name,
    t.description,
    t.business_impact,
    t.topic_type,
    t.sector,
    t.urgency,
    t.confidence,
    t.final_score,
    t.extraction_date,
    t.pipeline_iteration,
    COUNT(at.article_id) as article_count
FROM topics t
LEFT JOIN article_topics at ON t.id = at.topic_id
WHERE t.company_id IS NULL  -- Macro/political topics have no company
GROUP BY t.id, t.name, t.description, t.business_impact, t.topic_type, t.sector,
         t.urgency, t.confidence, t.final_score, t.extraction_date, t.pipeline_iteration
ORDER BY t.final_score DESC;

-- Step 7: Create view for recent macro topics (last 24 hours)
CREATE VIEW macro_topics_recent AS
SELECT
    t.*,
    COUNT(at.article_id) as article_count
FROM topics t
LEFT JOIN article_topics at ON t.id = at.topic_id
WHERE t.company_id IS NULL
  AND t.topic_type IN ('macro', 'political')
  AND t.extraction_date > NOW() - INTERVAL '24 hours'
GROUP BY t.id
ORDER BY t.final_score DESC;

-- Step 8: Create view combining company and macro topics for front page
CREATE VIEW front_page_topics AS
(
    -- High-urgency company topics
    SELECT
        t.id,
        c.name as entity_name,
        c.ticker,
        'company' as entity_type,
        t.name as topic_name,
        t.description,
        t.business_impact,
        t.urgency,
        t.confidence,
        t.final_score,
        t.extraction_date,
        t.topic_type
    FROM topics t
    JOIN companies c ON t.company_id = c.id
    WHERE t.urgency IN ('high', 'medium')
      AND t.final_score > 0.6
    ORDER BY t.final_score DESC
    LIMIT 10
)
UNION ALL
(
    -- Recent macro/political topics
    SELECT
        t.id,
        t.sector as entity_name,
        NULL as ticker,
        t.topic_type as entity_type,
        t.name as topic_name,
        t.description,
        t.business_impact,
        t.urgency,
        t.confidence,
        t.final_score,
        t.extraction_date,
        t.topic_type
    FROM topics t
    WHERE t.company_id IS NULL
      AND t.topic_type IN ('macro', 'political')
      AND t.extraction_date > NOW() - INTERVAL '24 hours'
    ORDER BY t.final_score DESC
    LIMIT 10
)
ORDER BY final_score DESC;

-- Step 9: Recreate company_topic_summary view to handle NULL company_id
CREATE VIEW company_topic_summary AS
SELECT
    COALESCE(c.name, 'Macro/Political') as company_name,
    c.ticker,
    COUNT(t.id) as total_topics,
    COUNT(CASE WHEN t.urgency = 'high' THEN 1 END) as high_urgency_topics,
    AVG(t.final_score) as avg_topic_score,
    MAX(t.extraction_date) as last_research_date
FROM topics t
LEFT JOIN companies c ON t.company_id = c.id
GROUP BY c.id, c.name, c.ticker;

-- Step 10: Add comments explaining the schema change
COMMENT ON COLUMN topics.company_id IS 'Foreign key to companies table. NULL for macro/political topics that are market-wide.';
COMMENT ON COLUMN topics.topic_type IS 'Type of topic: company_specific (default), macro (market-wide economic), or political (policy/elections).';
COMMENT ON COLUMN topics.sector IS 'Market sector for macro topics (e.g., "Monetary Policy", "Inflation"). NULL for company topics.';

-- Step 11: Create function to get topics by type
CREATE OR REPLACE FUNCTION get_topics_by_type(
    topic_type_param VARCHAR(50),
    limit_count INTEGER DEFAULT 10,
    hours_back INTEGER DEFAULT 24
)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR(500),
    description TEXT,
    business_impact TEXT,
    topic_type VARCHAR(50),
    sector VARCHAR(100),
    urgency VARCHAR(20),
    confidence DECIMAL(3,2),
    final_score DECIMAL(5,4),
    extraction_date TIMESTAMP,
    article_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.name,
        t.description,
        t.business_impact,
        t.topic_type,
        t.sector,
        t.urgency,
        t.confidence,
        t.final_score,
        t.extraction_date,
        COUNT(at.article_id) as article_count
    FROM topics t
    LEFT JOIN article_topics at ON t.id = at.topic_id
    WHERE t.topic_type = topic_type_param
      AND t.extraction_date > NOW() - INTERVAL '1 hour' * hours_back
    GROUP BY t.id, t.name, t.description, t.business_impact, t.topic_type,
             t.sector, t.urgency, t.confidence, t.final_score, t.extraction_date
    ORDER BY t.final_score DESC
    LIMIT limit_count;
END;
$$;

-- Verification queries (run these to confirm migration worked)
-- SELECT * FROM macro_political_topics LIMIT 5;
-- SELECT * FROM macro_topics_recent LIMIT 5;
-- SELECT * FROM front_page_topics LIMIT 20;
-- SELECT get_topics_by_type('macro', 10, 24);