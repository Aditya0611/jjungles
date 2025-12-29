-- Create scheduler settings table for admin-configurable scraper frequency
-- Migration: 009_create_scheduler_settings.sql
-- 
-- This migration creates a table to store scheduler settings that can be
-- updated by admins to change scraper run frequency without code changes.

-- Create scheduler_settings table
CREATE TABLE IF NOT EXISTS public.scheduler_settings (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL UNIQUE,  -- Platform name: 'tiktok', 'instagram', 'x', 'linkedin', 'facebook'
    enabled BOOLEAN NOT NULL DEFAULT true,  -- Whether scraper is enabled for this platform
    frequency_hours DOUBLE PRECISION NOT NULL DEFAULT 3.0,  -- Run every N hours (2-4 hours range)
    last_run_at TIMESTAMP WITH TIME ZONE NULL,  -- Last successful run timestamp
    next_run_at TIMESTAMP WITH TIME ZONE NULL,  -- Next scheduled run timestamp
    run_count BIGINT NOT NULL DEFAULT 0,  -- Total number of runs
    success_count BIGINT NOT NULL DEFAULT 0,  -- Number of successful runs
    failure_count BIGINT NOT NULL DEFAULT 0,  -- Number of failed runs
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB NULL,  -- Additional settings (region, headless, etc.)
    CONSTRAINT scheduler_settings_frequency_check CHECK (frequency_hours >= 0.5 AND frequency_hours <= 24.0)  -- Min 30min, max 24h
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_scheduler_settings_platform ON public.scheduler_settings USING BTREE (platform);
CREATE INDEX IF NOT EXISTS idx_scheduler_settings_enabled ON public.scheduler_settings USING BTREE (enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_scheduler_settings_next_run ON public.scheduler_settings USING BTREE (next_run_at) WHERE enabled = true;

-- Insert default settings for all platforms
INSERT INTO public.scheduler_settings (platform, enabled, frequency_hours, metadata) VALUES
    ('tiktok', true, 3.0, '{"region": "en", "headless": true, "upload_to_db": true}'),
    ('instagram', false, 3.0, '{"region": "en", "headless": true, "upload_to_db": true}'),
    ('x', false, 3.0, '{"region": "en", "headless": true, "upload_to_db": true}'),
    ('linkedin', false, 3.0, '{"region": "en", "headless": true, "upload_to_db": true}'),
    ('facebook', false, 3.0, '{"region": "en", "headless": true, "upload_to_db": true}')
ON CONFLICT (platform) DO NOTHING;

-- Create function to update next_run_at based on frequency
CREATE OR REPLACE FUNCTION update_next_run_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.last_run_at IS NOT NULL THEN
        NEW.next_run_at := NEW.last_run_at + (NEW.frequency_hours || ' hours')::INTERVAL;
    ELSIF NEW.next_run_at IS NULL THEN
        -- If no last_run_at, set next_run_at to now + frequency
        NEW.next_run_at := NOW() + (NEW.frequency_hours || ' hours')::INTERVAL;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update next_run_at
CREATE TRIGGER trigger_update_next_run_at
    BEFORE INSERT OR UPDATE ON public.scheduler_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_next_run_at();

-- Create function to get next platform to run
CREATE OR REPLACE FUNCTION get_next_platform_to_run()
RETURNS TABLE (
    platform TEXT,
    frequency_hours DOUBLE PRECISION,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.platform,
        s.frequency_hours,
        s.metadata
    FROM public.scheduler_settings s
    WHERE s.enabled = true
      AND (s.next_run_at IS NULL OR s.next_run_at <= NOW())
    ORDER BY s.next_run_at ASC NULLS FIRST
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Create function to update run statistics
CREATE OR REPLACE FUNCTION update_run_stats(
    p_platform TEXT,
    p_success BOOLEAN
)
RETURNS void AS $$
BEGIN
    UPDATE public.scheduler_settings
    SET 
        run_count = run_count + 1,
        success_count = CASE WHEN p_success THEN success_count + 1 ELSE success_count END,
        failure_count = CASE WHEN NOT p_success THEN failure_count + 1 ELSE failure_count END,
        last_run_at = CASE WHEN p_success THEN NOW() ELSE last_run_at END
    WHERE platform = p_platform;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE public.scheduler_settings IS 'Stores scheduler settings for each platform. Admins can update frequency_hours to change run frequency.';
COMMENT ON COLUMN public.scheduler_settings.platform IS 'Platform name: tiktok, instagram, x, linkedin, facebook';
COMMENT ON COLUMN public.scheduler_settings.enabled IS 'Whether scraper is enabled for this platform';
COMMENT ON COLUMN public.scheduler_settings.frequency_hours IS 'Run every N hours (default: 3.0, range: 0.5-24.0)';
COMMENT ON COLUMN public.scheduler_settings.last_run_at IS 'Timestamp of last successful run';
COMMENT ON COLUMN public.scheduler_settings.next_run_at IS 'Timestamp of next scheduled run (auto-calculated)';
COMMENT ON COLUMN public.scheduler_settings.metadata IS 'Additional platform-specific settings (region, headless, etc.)';

-- Example admin queries:

-- Update frequency for TikTok to run every 2 hours
-- UPDATE public.scheduler_settings SET frequency_hours = 2.0 WHERE platform = 'tiktok';

-- Update frequency for Instagram to run every 4 hours
-- UPDATE public.scheduler_settings SET frequency_hours = 4.0 WHERE platform = 'instagram';

-- Enable/disable a platform
-- UPDATE public.scheduler_settings SET enabled = true WHERE platform = 'tiktok';
-- UPDATE public.scheduler_settings SET enabled = false WHERE platform = 'instagram';

-- Get all scheduler settings
-- SELECT * FROM public.scheduler_settings ORDER BY platform;

-- Get next platform to run
-- SELECT * FROM get_next_platform_to_run();

