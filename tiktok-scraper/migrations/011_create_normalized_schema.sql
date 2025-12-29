-- Create normalized schema for trends, versions, sources, and metrics
-- Migration: 011_create_normalized_schema.sql
-- 
-- This migration creates a normalized database schema with separate tables for:
-- - trend: Core trend information
-- - trend_version: Versioned trend data (for daily snapshots)
-- - source: Source/platform information
-- - metric: Engagement and performance metrics
--
-- This schema supports better data organization and querying across platforms.

-- ============================================================================
-- SOURCE TABLE
-- ============================================================================

-- Create source table for platforms
CREATE TABLE IF NOT EXISTS public.source (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL UNIQUE,  -- Platform name: 'tiktok', 'instagram', 'x', 'linkedin', 'facebook'
    display_name TEXT NOT NULL,  -- Display name: 'TikTok', 'Instagram', etc.
    enabled BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NULL,  -- Platform-specific metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index on source platform
CREATE INDEX IF NOT EXISTS idx_source_platform ON public.source USING BTREE (platform);
CREATE INDEX IF NOT EXISTS idx_source_enabled ON public.source USING BTREE (enabled) WHERE enabled = true;

-- Insert default sources
INSERT INTO public.source (platform, display_name, enabled, metadata) VALUES
    ('tiktok', 'TikTok', true, '{"region": "en", "headless": true}'),
    ('instagram', 'Instagram', false, '{"region": "en", "headless": true}'),
    ('x', 'X (Twitter)', false, '{"region": "en", "headless": true}'),
    ('linkedin', 'LinkedIn', false, '{"region": "en", "headless": true}'),
    ('facebook', 'Facebook', false, '{"region": "en", "headless": true}')
ON CONFLICT (platform) DO NOTHING;

-- ============================================================================
-- TREND TABLE
-- ============================================================================

-- Create trend table for core trend information
CREATE TABLE IF NOT EXISTS public.trend (
    id BIGSERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES public.source(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,  -- Hashtag or topic name (e.g., '#viral', 'trending_topic')
    normalized_topic TEXT NOT NULL,  -- Normalized topic (lowercase, no special chars)
    first_discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),  -- First time this trend was seen
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),  -- Most recent sighting
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'declining', 'archived'
    metadata JSONB NULL,  -- Additional trend metadata (category, tags, etc.)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT trend_source_topic_unique UNIQUE (source_id, normalized_topic)
);

-- Create indexes on trend table
CREATE INDEX IF NOT EXISTS idx_trend_source_id ON public.trend USING BTREE (source_id);
CREATE INDEX IF NOT EXISTS idx_trend_topic ON public.trend USING BTREE (topic);
CREATE INDEX IF NOT EXISTS idx_trend_normalized_topic ON public.trend USING BTREE (normalized_topic);
CREATE INDEX IF NOT EXISTS idx_trend_status ON public.trend USING BTREE (status);
CREATE INDEX IF NOT EXISTS idx_trend_first_discovered ON public.trend USING BTREE (first_discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_last_seen ON public.trend USING BTREE (last_seen_at DESC);

-- Composite index: (platform, discovered_at) via join
-- Note: This requires joining with source table, but we'll create a view for convenience
CREATE INDEX IF NOT EXISTS idx_trend_source_discovered ON public.trend USING BTREE (source_id, first_discovered_at DESC);

-- ============================================================================
-- TREND_VERSION TABLE
-- ============================================================================

-- Create trend_version table for versioned trend data (daily snapshots)
CREATE TABLE IF NOT EXISTS public.trend_version (
    id BIGSERIAL PRIMARY KEY,
    trend_id BIGINT NOT NULL REFERENCES public.trend(id) ON DELETE CASCADE,
    version_date DATE NOT NULL,  -- Date of this version (YYYY-MM-DD)
    version_number INTEGER NOT NULL DEFAULT 1,  -- Version number for this date (1, 2, 3...)
    engagement_score DOUBLE PRECISION NULL,  -- Calculated engagement score (1.0-10.0)
    sentiment_polarity DOUBLE PRECISION NULL,  -- Sentiment polarity (-1.0 to 1.0)
    sentiment_label TEXT NULL,  -- Sentiment label (Positive/Neutral/Negative)
    language TEXT NULL,  -- Detected language code (ISO 639-1)
    language_confidence DOUBLE PRECISION NULL,  -- Language detection confidence (0.0-1.0)
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),  -- When this version was scraped
    version_id UUID NULL,  -- Scraper run session ID
    metadata JSONB NULL,  -- Additional version metadata (caption, title, post_format, sound, etc.)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT trend_version_unique UNIQUE (trend_id, version_date, version_number)
);

-- Create indexes on trend_version table
CREATE INDEX IF NOT EXISTS idx_trend_version_trend_id ON public.trend_version USING BTREE (trend_id);
CREATE INDEX IF NOT EXISTS idx_trend_version_date ON public.trend_version USING BTREE (version_date DESC);
CREATE INDEX IF NOT EXISTS idx_trend_version_engagement ON public.trend_version USING BTREE (engagement_score DESC);  -- Index on engagement_score
CREATE INDEX IF NOT EXISTS idx_trend_version_scraped_at ON public.trend_version USING BTREE (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_version_language ON public.trend_version USING BTREE (language) WHERE language IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trend_version_sentiment ON public.trend_version USING BTREE (sentiment_label) WHERE sentiment_label IS NOT NULL;

-- Composite index for version queries
CREATE INDEX IF NOT EXISTS idx_trend_version_trend_date ON public.trend_version USING BTREE (trend_id, version_date DESC, version_number DESC);

-- ============================================================================
-- METRIC TABLE
-- ============================================================================

-- Create metric table for engagement and performance metrics
CREATE TABLE IF NOT EXISTS public.metric (
    id BIGSERIAL PRIMARY KEY,
    trend_version_id BIGINT NOT NULL REFERENCES public.trend_version(id) ON DELETE CASCADE,
    metric_type TEXT NOT NULL,  -- 'posts', 'views', 'likes', 'shares', 'comments', etc.
    metric_value BIGINT NOT NULL,  -- Metric value
    metric_unit TEXT NULL DEFAULT 'count',  -- Unit: 'count', 'percentage', etc.
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB NULL,  -- Additional metric metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT metric_type_check CHECK (metric_type IN ('posts', 'views', 'likes', 'shares', 'comments', 'followers', 'engagement_rate', 'other'))
);

-- Create indexes on metric table
CREATE INDEX IF NOT EXISTS idx_metric_trend_version_id ON public.metric USING BTREE (trend_version_id);
CREATE INDEX IF NOT EXISTS idx_metric_type ON public.metric USING BTREE (metric_type);
CREATE INDEX IF NOT EXISTS idx_metric_collected_at ON public.metric USING BTREE (collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_value ON public.metric USING BTREE (metric_value DESC);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_metric_version_type ON public.metric USING BTREE (trend_version_id, metric_type);

-- ============================================================================
-- VIEWS FOR CONVENIENCE
-- ============================================================================

-- View: trend_with_source - Join trend with source for easy querying
CREATE OR REPLACE VIEW trend_with_source AS
SELECT 
    t.id,
    t.topic,
    t.normalized_topic,
    t.first_discovered_at,
    t.last_seen_at,
    t.status,
    s.platform,
    s.display_name as platform_display_name,
    t.metadata as trend_metadata,
    t.created_at,
    t.updated_at
FROM public.trend t
JOIN public.source s ON t.source_id = s.id;

-- View: trend_version_with_details - Join trend_version with trend and source
CREATE OR REPLACE VIEW trend_version_with_details AS
SELECT 
    tv.id,
    tv.trend_id,
    tv.version_date,
    tv.version_number,
    tv.engagement_score,
    tv.sentiment_polarity,
    tv.sentiment_label,
    tv.language,
    tv.language_confidence,
    tv.scraped_at,
    t.topic,
    t.normalized_topic,
    s.platform,
    s.display_name as platform_display_name,
    t.first_discovered_at,
    tv.metadata as version_metadata,
    tv.created_at
FROM public.trend_version tv
JOIN public.trend t ON tv.trend_id = t.id
JOIN public.source s ON t.source_id = s.id;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Get or create trend
CREATE OR REPLACE FUNCTION get_or_create_trend(
    p_source_platform TEXT,
    p_topic TEXT,
    p_normalized_topic TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_source_id INTEGER;
    v_trend_id BIGINT;
    v_normalized TEXT;
BEGIN
    -- Get source ID
    SELECT id INTO v_source_id FROM public.source WHERE platform = p_source_platform;
    
    IF v_source_id IS NULL THEN
        RAISE EXCEPTION 'Source not found: %', p_source_platform;
    END IF;
    
    -- Normalize topic if not provided
    v_normalized := COALESCE(p_normalized_topic, LOWER(REGEXP_REPLACE(p_topic, '[^a-z0-9]', '', 'g')));
    
    -- Try to get existing trend
    SELECT id INTO v_trend_id 
    FROM public.trend 
    WHERE source_id = v_source_id AND normalized_topic = v_normalized;
    
    -- Create if not exists
    IF v_trend_id IS NULL THEN
        INSERT INTO public.trend (source_id, topic, normalized_topic, first_discovered_at, last_seen_at)
        VALUES (v_source_id, p_topic, v_normalized, NOW(), NOW())
        RETURNING id INTO v_trend_id;
    ELSE
        -- Update last_seen_at
        UPDATE public.trend 
        SET last_seen_at = NOW(), updated_at = NOW()
        WHERE id = v_trend_id;
    END IF;
    
    RETURN v_trend_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get latest version for a trend on a date
CREATE OR REPLACE FUNCTION get_latest_trend_version(
    p_trend_id BIGINT,
    p_version_date DATE
)
RETURNS INTEGER AS $$
DECLARE
    v_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version_number), 0) INTO v_version
    FROM public.trend_version
    WHERE trend_id = p_trend_id AND version_date = p_version_date;
    
    RETURN v_version + 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE public.source IS 'Platform sources (TikTok, Instagram, X, LinkedIn, Facebook)';
COMMENT ON TABLE public.trend IS 'Core trend information. Each trend represents a unique topic/hashtag per platform.';
COMMENT ON TABLE public.trend_version IS 'Versioned trend data for daily snapshots. Multiple versions per day supported.';
COMMENT ON TABLE public.metric IS 'Engagement and performance metrics for trend versions (posts, views, likes, etc.)';

COMMENT ON COLUMN public.trend.topic IS 'Original topic/hashtag name (e.g., "#viral")';
COMMENT ON COLUMN public.trend.normalized_topic IS 'Normalized topic for deduplication (lowercase, no special chars)';
COMMENT ON COLUMN public.trend.first_discovered_at IS 'First time this trend was discovered';
COMMENT ON COLUMN public.trend.last_seen_at IS 'Most recent time this trend was seen';
COMMENT ON COLUMN public.trend_version.engagement_score IS 'Calculated engagement score (1.0-10.0)';
COMMENT ON COLUMN public.trend_version.version_date IS 'Date of this version snapshot (YYYY-MM-DD)';
COMMENT ON COLUMN public.trend_version.version_number IS 'Version number for this date (increments per day)';

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Get trends by platform with discovery date
-- SELECT platform, topic, first_discovered_at, engagement_score
-- FROM trend_with_source t
-- JOIN trend_version tv ON t.id = tv.trend_id
-- WHERE platform = 'tiktok'
--   AND tv.version_date = CURRENT_DATE
-- ORDER BY tv.engagement_score DESC
-- LIMIT 20;

-- Get trends with engagement score index
-- SELECT topic, engagement_score, version_date
-- FROM trend_version_with_details
-- WHERE platform = 'tiktok'
--   AND engagement_score >= 7.0
-- ORDER BY engagement_score DESC, version_date DESC;

-- Get metrics for a trend version
-- SELECT metric_type, metric_value, collected_at
-- FROM metric
-- WHERE trend_version_id = 123
-- ORDER BY collected_at DESC;

