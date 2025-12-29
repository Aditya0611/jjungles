-- Add trend lifecycle tracking support
-- Migration: 003_add_trend_lifecycle_tracking.sql
-- 
-- This migration adds support for tracking trend lifecycle:
-- - When trend first appeared (first_seen)
-- - When it peaked (peak_time, peak_score)
-- - If it's decaying (is_decaying, decay_rate)
-- - Trend status (emerging, rising, peak, decaying, stale)
--
-- Note: Trend lifecycle data is stored in the metadata JSONB column
-- for flexibility. No schema changes needed, but this migration
-- adds indexes for efficient querying.

-- Create index on metadata->>'trend_status' for filtering by trend status
CREATE INDEX IF NOT EXISTS idx_tiktok_trend_status 
ON public.tiktok USING BTREE ((metadata->>'trend_status')) 
WHERE metadata->>'trend_status' IS NOT NULL;

-- Create index on metadata->>'trend_lifecycle'->>'first_seen' for finding new trends
CREATE INDEX IF NOT EXISTS idx_tiktok_first_seen 
ON public.tiktok USING BTREE ((metadata->'trend_lifecycle'->>'first_seen'))
WHERE metadata->'trend_lifecycle'->>'first_seen' IS NOT NULL;

-- Create index on metadata->>'trend_lifecycle'->>'is_decaying' for finding decaying trends
CREATE INDEX IF NOT EXISTS idx_tiktok_is_decaying 
ON public.tiktok USING BTREE ((metadata->'trend_lifecycle'->>'is_decaying'))
WHERE metadata->'trend_lifecycle'->>'is_decaying' = 'true';

-- Add comments
COMMENT ON COLUMN public.tiktok.metadata IS 'Additional metadata including trend_lifecycle: {first_seen, peak_time, peak_score, is_decaying, decay_rate, trend_status}';

-- Example queries for trend analysis:

-- Find emerging trends (first seen in last hour)
-- SELECT topic, engagement_score, metadata->'trend_lifecycle'->>'first_seen' as first_seen
-- FROM public.tiktok
-- WHERE metadata->'trend_lifecycle'->>'trend_status' = 'emerging'
--   AND scraped_at > NOW() - INTERVAL '1 hour'
-- ORDER BY engagement_score DESC;

-- Find decaying trends
-- SELECT topic, engagement_score, 
--        metadata->'trend_lifecycle'->>'decay_rate' as decay_rate,
--        metadata->'trend_lifecycle'->>'peak_score' as peak_score
-- FROM public.tiktok
-- WHERE metadata->'trend_lifecycle'->>'is_decaying' = 'true'
-- ORDER BY engagement_score DESC;

-- Find trends at peak
-- SELECT topic, engagement_score, 
--        metadata->'trend_lifecycle'->>'peak_time' as peak_time
-- FROM public.tiktok
-- WHERE metadata->'trend_lifecycle'->>'trend_status' = 'peak'
-- ORDER BY engagement_score DESC;

