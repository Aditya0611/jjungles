-- Add daily snapshot/versioning support for trend comparison
-- Migration: 006_add_daily_snapshots.sql
-- 
-- This migration adds support for daily snapshots and versioning:
-- - snapshot_date: Date when snapshot was taken (for daily grouping)
-- - snapshot_version: Version number within the day (1, 2, 3...)
-- - Enables comparison of trends across different days and times

-- Add snapshot columns to existing table
ALTER TABLE public.tiktok 
ADD COLUMN IF NOT EXISTS snapshot_date DATE NULL;

ALTER TABLE public.tiktok 
ADD COLUMN IF NOT EXISTS snapshot_version INTEGER NULL DEFAULT 1;

-- Create index for snapshot_date for efficient daily queries
CREATE INDEX IF NOT EXISTS idx_tiktok_snapshot_date 
ON public.tiktok USING BTREE (snapshot_date DESC) 
WHERE snapshot_date IS NOT NULL;

-- Create composite index for snapshot_date + topic (for trend tracking)
CREATE INDEX IF NOT EXISTS idx_tiktok_snapshot_topic 
ON public.tiktok USING BTREE (snapshot_date, topic) 
WHERE snapshot_date IS NOT NULL;

-- Create composite index for snapshot_date + engagement_score (for daily rankings)
CREATE INDEX IF NOT EXISTS idx_tiktok_snapshot_engagement 
ON public.tiktok USING BTREE (snapshot_date, engagement_score DESC) 
WHERE snapshot_date IS NOT NULL;

-- Create index for snapshot_version (for version tracking within a day)
CREATE INDEX IF NOT EXISTS idx_tiktok_snapshot_version 
ON public.tiktok USING BTREE (snapshot_date, snapshot_version) 
WHERE snapshot_date IS NOT NULL;

-- Add column comments
COMMENT ON COLUMN public.tiktok.snapshot_date IS 'Date when snapshot was taken (YYYY-MM-DD). Used for daily trend comparison.';
COMMENT ON COLUMN public.tiktok.snapshot_version IS 'Version number within the snapshot date (1, 2, 3...). Allows multiple snapshots per day.';

-- Create a view for latest daily snapshots (most recent version per day)
CREATE OR REPLACE VIEW public.tiktok_daily_latest AS
SELECT DISTINCT ON (snapshot_date, topic)
    *
FROM public.tiktok
WHERE snapshot_date IS NOT NULL
ORDER BY snapshot_date DESC, topic, snapshot_version DESC;

-- Create a view for daily trend summaries
CREATE OR REPLACE VIEW public.tiktok_daily_summary AS
SELECT 
    snapshot_date,
    COUNT(DISTINCT topic) as unique_hashtags,
    AVG(engagement_score) as avg_engagement_score,
    MAX(engagement_score) as max_engagement_score,
    MIN(engagement_score) as min_engagement_score,
    COUNT(*) as total_records,
    MAX(snapshot_version) as latest_version
FROM public.tiktok
WHERE snapshot_date IS NOT NULL
GROUP BY snapshot_date
ORDER BY snapshot_date DESC;

-- Example queries for trend comparison:

-- Compare trends across two dates
-- SELECT 
--     t1.topic,
--     t1.engagement_score as score_date1,
--     t2.engagement_score as score_date2,
--     (t2.engagement_score - t1.engagement_score) as score_change,
--     t1.snapshot_date as date1,
--     t2.snapshot_date as date2
-- FROM public.tiktok t1
-- JOIN public.tiktok t2 ON t1.topic = t2.topic
-- WHERE t1.snapshot_date = '2024-01-15'
--   AND t2.snapshot_date = '2024-01-16'
--   AND t1.snapshot_version = (SELECT MAX(snapshot_version) FROM public.tiktok WHERE snapshot_date = t1.snapshot_date AND topic = t1.topic)
--   AND t2.snapshot_version = (SELECT MAX(snapshot_version) FROM public.tiktok WHERE snapshot_date = t2.snapshot_date AND topic = t2.topic)
-- ORDER BY score_change DESC;

-- Get trending hashtags for a specific date
-- SELECT topic, engagement_score, posts, sentiment_label
-- FROM public.tiktok
-- WHERE snapshot_date = CURRENT_DATE
--   AND snapshot_version = (SELECT MAX(snapshot_version) FROM public.tiktok WHERE snapshot_date = CURRENT_DATE)
-- ORDER BY engagement_score DESC
-- LIMIT 20;

-- Track trend growth over multiple days
-- SELECT 
--     snapshot_date,
--     topic,
--     engagement_score,
--     LAG(engagement_score) OVER (PARTITION BY topic ORDER BY snapshot_date) as previous_score,
--     engagement_score - LAG(engagement_score) OVER (PARTITION BY topic ORDER BY snapshot_date) as score_delta
-- FROM public.tiktok
-- WHERE topic = '#viral'
--   AND snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
-- ORDER BY snapshot_date DESC;

