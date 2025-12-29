-- Create run history table for tracking scraper execution history
-- Migration: 010_create_run_history.sql
-- 
-- This migration creates a table to store detailed run history including:
-- - Start and end timestamps
-- - Record counts
-- - Error information
-- - Platform and configuration details

-- Create run_history table
CREATE TABLE IF NOT EXISTS public.run_history (
    id BIGSERIAL PRIMARY KEY,
    platform TEXT NOT NULL,  -- Platform name: 'tiktok', 'instagram', 'x', 'linkedin', 'facebook'
    job_id TEXT NULL,  -- Job identifier (for worker systems)
    status TEXT NOT NULL,  -- 'running', 'completed', 'failed', 'cancelled'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE NULL,  -- NULL if still running
    duration_seconds DOUBLE PRECISION NULL,  -- Calculated duration
    records_scraped INTEGER NULL DEFAULT 0,  -- Number of records scraped
    records_uploaded INTEGER NULL DEFAULT 0,  -- Number of records uploaded to database
    error_message TEXT NULL,  -- Error message if failed
    error_traceback TEXT NULL,  -- Full error traceback if available
    metadata JSONB NULL,  -- Additional metadata (region, headless, version_id, etc.)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT run_history_status_check CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_run_history_platform ON public.run_history USING BTREE (platform);
CREATE INDEX IF NOT EXISTS idx_run_history_status ON public.run_history USING BTREE (status);
CREATE INDEX IF NOT EXISTS idx_run_history_started_at ON public.run_history USING BTREE (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_run_history_platform_started ON public.run_history USING BTREE (platform, started_at DESC);

-- Composite index for recent runs by platform
CREATE INDEX IF NOT EXISTS idx_run_history_platform_recent ON public.run_history USING BTREE (platform, started_at DESC) 
WHERE started_at >= NOW() - INTERVAL '30 days';

-- Create function to update run history on completion
CREATE OR REPLACE FUNCTION update_run_history(
    p_run_id BIGINT,
    p_status TEXT,
    p_records_scraped INTEGER DEFAULT 0,
    p_records_uploaded INTEGER DEFAULT 0,
    p_error_message TEXT DEFAULT NULL,
    p_error_traceback TEXT DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE public.run_history
    SET 
        status = p_status,
        ended_at = NOW(),
        duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
        records_scraped = p_records_scraped,
        records_uploaded = p_records_uploaded,
        error_message = p_error_message,
        error_traceback = p_error_traceback
    WHERE id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Create function to get run statistics
CREATE OR REPLACE FUNCTION get_run_statistics(
    p_platform TEXT DEFAULT NULL,
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    platform TEXT,
    total_runs BIGINT,
    successful_runs BIGINT,
    failed_runs BIGINT,
    avg_duration_seconds DOUBLE PRECISION,
    avg_records_scraped DOUBLE PRECISION,
    last_run_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(p_platform, rh.platform) as platform,
        COUNT(*) as total_runs,
        COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
        COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
        AVG(duration_seconds) as avg_duration_seconds,
        AVG(records_scraped) as avg_records_scraped,
        MAX(started_at) as last_run_at
    FROM public.run_history rh
    WHERE started_at >= NOW() - (p_days || ' days')::INTERVAL
      AND (p_platform IS NULL OR rh.platform = p_platform)
    GROUP BY rh.platform
    ORDER BY rh.platform;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE public.run_history IS 'Stores detailed execution history for scraper runs including start/end times, record counts, and errors.';
COMMENT ON COLUMN public.run_history.platform IS 'Platform name: tiktok, instagram, x, linkedin, facebook';
COMMENT ON COLUMN public.run_history.job_id IS 'Job identifier from worker system (APScheduler, Celery, etc.)';
COMMENT ON COLUMN public.run_history.status IS 'Run status: running, completed, failed, cancelled';
COMMENT ON COLUMN public.run_history.duration_seconds IS 'Execution duration in seconds (calculated on completion)';
COMMENT ON COLUMN public.run_history.records_scraped IS 'Number of records scraped during this run';
COMMENT ON COLUMN public.run_history.records_uploaded IS 'Number of records successfully uploaded to database';
COMMENT ON COLUMN public.run_history.error_message IS 'Error message if run failed';
COMMENT ON COLUMN public.run_history.error_traceback IS 'Full error traceback if available';

-- Example queries:

-- Get recent runs for a platform
-- SELECT * FROM public.run_history 
-- WHERE platform = 'tiktok' 
-- ORDER BY started_at DESC 
-- LIMIT 10;

-- Get run statistics for last 7 days
-- SELECT * FROM get_run_statistics('tiktok', 7);

-- Get failed runs
-- SELECT * FROM public.run_history 
-- WHERE status = 'failed' 
-- ORDER BY started_at DESC 
-- LIMIT 20;

-- Get average performance metrics
-- SELECT 
--     platform,
--     AVG(duration_seconds) as avg_duration,
--     AVG(records_scraped) as avg_records,
--     COUNT(*) as total_runs
-- FROM public.run_history
-- WHERE started_at >= NOW() - INTERVAL '7 days'
-- GROUP BY platform;

