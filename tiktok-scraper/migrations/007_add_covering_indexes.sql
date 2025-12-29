-- Add covering indexes for common query patterns
-- Migration: 007_add_covering_indexes.sql
-- 
-- Covering indexes include all columns needed for a query, allowing index-only scans
-- which are much faster than index + table lookups. This improves query performance
-- for common access patterns.

-- ============================================================================
-- COVERING INDEXES FOR COMMON QUERY PATTERNS
-- ============================================================================

-- 1. Daily snapshot queries with engagement score (most common)
-- Covers: snapshot_date, engagement_score, topic, sentiment, posts, language
CREATE INDEX IF NOT EXISTS idx_tiktok_snapshot_covering_engagement 
ON public.tiktok USING BTREE (snapshot_date DESC, engagement_score DESC) 
INCLUDE (topic, sentiment_label, posts, views, language, language_confidence, platform)
WHERE snapshot_date IS NOT NULL;

-- 2. Language-based trending queries
-- Covers: language, engagement_score, topic, sentiment, snapshot_date
CREATE INDEX IF NOT EXISTS idx_tiktok_language_covering_trending 
ON public.tiktok USING BTREE (language, engagement_score DESC, snapshot_date DESC) 
INCLUDE (topic, sentiment_label, posts, views, language_confidence)
WHERE language IS NOT NULL;

-- 3. Platform + date queries with full record data
-- Covers: platform, scraped_at, topic, engagement_score
CREATE INDEX IF NOT EXISTS idx_tiktok_platform_date_covering 
ON public.tiktok USING BTREE (platform, scraped_at DESC) 
INCLUDE (topic, engagement_score, sentiment_label, posts, views, language, snapshot_date)
WHERE platform IS NOT NULL;

-- 4. Topic history queries (for trend lifecycle)
-- Covers: topic, scraped_at, engagement_score, snapshot_date
CREATE INDEX IF NOT EXISTS idx_tiktok_topic_history_covering 
ON public.tiktok USING BTREE (topic, scraped_at DESC) 
INCLUDE (engagement_score, sentiment_label, posts, snapshot_date, snapshot_version, version_id)
WHERE topic IS NOT NULL;

-- 5. Daily summary queries (aggregations)
-- Covers: snapshot_date, engagement_score, language
CREATE INDEX IF NOT EXISTS idx_tiktok_daily_summary_covering 
ON public.tiktok USING BTREE (snapshot_date DESC) 
INCLUDE (topic, engagement_score, language, sentiment_label, posts)
WHERE snapshot_date IS NOT NULL;

-- 6. Trend comparison queries (two dates)
-- Covers: snapshot_date, topic, engagement_score
CREATE INDEX IF NOT EXISTS idx_tiktok_trend_comparison_covering 
ON public.tiktok USING BTREE (snapshot_date, topic) 
INCLUDE (engagement_score, sentiment_label, posts, views, language, snapshot_version)
WHERE snapshot_date IS NOT NULL AND topic IS NOT NULL;

-- 7. High-confidence language queries
-- Covers: language, language_confidence, engagement_score
CREATE INDEX IF NOT EXISTS idx_tiktok_language_confidence_covering 
ON public.tiktok USING BTREE (language, language_confidence DESC, engagement_score DESC) 
INCLUDE (topic, sentiment_label, posts, snapshot_date)
WHERE language IS NOT NULL AND language_confidence > 0.7;

-- 8. Sentiment-based queries
-- Covers: sentiment_label, engagement_score, snapshot_date
CREATE INDEX IF NOT EXISTS idx_tiktok_sentiment_covering 
ON public.tiktok USING BTREE (sentiment_label, engagement_score DESC, snapshot_date DESC) 
INCLUDE (topic, sentiment_polarity, posts, language)
WHERE sentiment_label IS NOT NULL;

-- ============================================================================
-- COMPOSITE INDEXES FOR SPECIFIC QUERY PATTERNS
-- ============================================================================

-- 9. Latest snapshot per topic (for deduplication)
-- Used for getting latest version per topic per date
CREATE INDEX IF NOT EXISTS idx_tiktok_latest_snapshot 
ON public.tiktok USING BTREE (snapshot_date DESC, topic, snapshot_version DESC) 
INCLUDE (engagement_score, sentiment_label, posts, language)
WHERE snapshot_date IS NOT NULL AND topic IS NOT NULL;

-- 10. Version tracking within a day
-- Used for intraday version queries
CREATE INDEX IF NOT EXISTS idx_tiktok_version_tracking 
ON public.tiktok USING BTREE (snapshot_date, snapshot_version, topic) 
INCLUDE (engagement_score, scraped_at)
WHERE snapshot_date IS NOT NULL;

-- ============================================================================
-- PARTIAL INDEXES FOR FILTERED QUERIES
-- ============================================================================

-- 11. High-engagement trends only (for performance on large tables)
CREATE INDEX IF NOT EXISTS idx_tiktok_high_engagement_covering 
ON public.tiktok USING BTREE (snapshot_date DESC, engagement_score DESC) 
INCLUDE (topic, sentiment_label, posts, language)
WHERE engagement_score >= 7.0 AND snapshot_date IS NOT NULL;

-- 12. Recent trends only (last 7 days)
CREATE INDEX IF NOT EXISTS idx_tiktok_recent_trends_covering 
ON public.tiktok USING BTREE (snapshot_date DESC, engagement_score DESC) 
INCLUDE (topic, sentiment_label, posts, language, snapshot_version)
WHERE snapshot_date >= CURRENT_DATE - INTERVAL '7 days';

-- ============================================================================
-- INDEX MAINTENANCE
-- ============================================================================

-- Add comments
COMMENT ON INDEX idx_tiktok_snapshot_covering_engagement IS 'Covering index for daily snapshot queries with engagement scores. Enables index-only scans.';
COMMENT ON INDEX idx_tiktok_language_covering_trending IS 'Covering index for language-based trending queries. Includes all commonly accessed columns.';
COMMENT ON INDEX idx_tiktok_platform_date_covering IS 'Covering index for platform + date queries. Optimizes time-series queries.';
COMMENT ON INDEX idx_tiktok_topic_history_covering IS 'Covering index for topic history queries. Used for trend lifecycle analysis.';
COMMENT ON INDEX idx_tiktok_daily_summary_covering IS 'Covering index for daily summary aggregations. Optimizes GROUP BY queries.';
COMMENT ON INDEX idx_tiktok_trend_comparison_covering IS 'Covering index for trend comparison queries between dates.';
COMMENT ON INDEX idx_tiktok_language_confidence_covering IS 'Covering index for high-confidence language queries.';
COMMENT ON INDEX idx_tiktok_sentiment_covering IS 'Covering index for sentiment-based queries.';
COMMENT ON INDEX idx_tiktok_latest_snapshot IS 'Composite index for getting latest snapshot per topic per date.';
COMMENT ON INDEX idx_tiktok_version_tracking IS 'Index for version tracking within a day.';
COMMENT ON INDEX idx_tiktok_high_engagement_covering IS 'Partial covering index for high-engagement trends only.';
COMMENT ON INDEX idx_tiktok_recent_trends_covering IS 'Partial covering index for recent trends (last 7 days).';

-- ============================================================================
-- INDEX STATISTICS
-- ============================================================================

-- Analyze indexes after creation
ANALYZE public.tiktok;

-- ============================================================================
-- NOTES
-- ============================================================================

-- Covering indexes use the INCLUDE clause to add columns to the index
-- without affecting the sort order. This allows PostgreSQL to:
-- 1. Use index-only scans (no table lookups needed)
-- 2. Reduce I/O operations
-- 3. Improve query performance significantly

-- Partial indexes (with WHERE clause) are smaller and faster for filtered queries
-- They only index rows matching the condition, reducing index size and maintenance cost

-- Index maintenance:
-- - VACUUM ANALYZE should be run regularly (see maintenance policy)
-- - Index bloat can be monitored with pg_stat_user_indexes
-- - REINDEX may be needed if indexes become corrupted

