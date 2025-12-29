-- Dynamic Configuration Schema Extension
-- Add this to your existing schema.sql or run separately

-- Scraper Configuration Table
CREATE TABLE IF NOT EXISTS scraper_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform TEXT NOT NULL UNIQUE,
    interval_hours INT DEFAULT 3 CHECK (interval_hours > 0),
    enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default configuration for Instagram
INSERT INTO scraper_config (platform, interval_hours, enabled)
VALUES ('Instagram', 3, TRUE)
ON CONFLICT (platform) DO NOTHING;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_scraper_config_platform ON scraper_config(platform);

-- Optional: Scraping Logs Table (for requirement tracking)
CREATE TABLE IF NOT EXISTS scraping_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform TEXT NOT NULL,
    status TEXT NOT NULL, -- 'running', 'success', 'failed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    trends_found INT DEFAULT 0,
    error_message TEXT,
    version_id TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for scraping logs
CREATE INDEX IF NOT EXISTS idx_scraping_logs_platform ON scraping_logs(platform);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_started_at ON scraping_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_status ON scraping_logs(status);
