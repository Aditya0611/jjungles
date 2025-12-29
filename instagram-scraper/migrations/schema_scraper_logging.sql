-- Database schema for scraper run logging.
-- Tracks every scraper job execution with start, status, and results.

-- Scraper Runs Table
-- Tracks each execution of run_scraper_job()
CREATE TABLE IF NOT EXISTS scraper_runs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'running', -- 'running', 'success', 'failed'
    
    -- Results (for successful runs)
    hashtags_discovered INTEGER DEFAULT 0,
    hashtags_saved INTEGER DEFAULT 0,
    new_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    
    -- Error tracking (for failed runs)
    error_message TEXT,
    error_type VARCHAR(100),
    
    -- Metadata
    version_id VARCHAR(100),
    proxy_used VARCHAR(255),
    proxy_pool_size INTEGER,
    
    -- Configuration snapshot
    config_snapshot JSONB,
    
    -- Indexes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_scraper_runs_started_at ON scraper_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_status ON scraper_runs(status);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_version_id ON scraper_runs(version_id);

-- Optional: Scraper Logs Table for detailed step-by-step logging
CREATE TABLE IF NOT EXISTS scraper_logs (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES scraper_runs(id) ON DELETE CASCADE,
    
    -- Log entry
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'DEBUG'
    message TEXT NOT NULL,
    
    -- Context
    step VARCHAR(100), -- 'browser_launch', 'login', 'discovery', 'analysis', 'save'
    metadata JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scraper_logs_run_id ON scraper_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_scraper_logs_timestamp ON scraper_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_scraper_logs_level ON scraper_logs(level);

-- View for recent runs summary
CREATE OR REPLACE VIEW scraper_runs_summary AS
SELECT 
    id,
    started_at,
    completed_at,
    duration_seconds,
    status,
    hashtags_saved,
    error_message,
    CASE 
        WHEN status = 'success' THEN '✅'
        WHEN status = 'failed' THEN '❌'
        ELSE '⏳'
    END as status_icon
FROM scraper_runs
ORDER BY started_at DESC
LIMIT 100;

-- Function to automatically calculate duration on completion
CREATE OR REPLACE FUNCTION update_scraper_run_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND OLD.completed_at IS NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_duration
    BEFORE UPDATE ON scraper_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_scraper_run_duration();
