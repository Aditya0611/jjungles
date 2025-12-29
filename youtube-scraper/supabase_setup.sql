-- Create a unified table for storing trending topics/hashtags from all platforms
CREATE TABLE IF NOT EXISTS public.youtube (
    id BIGSERIAL PRIMARY KEY,
    platform TEXT NOT NULL,                -- e.g., 'youtube'
    topic_hashtag TEXT NOT NULL,           -- The trending topic or hahstag
    engagement_score FLOAT,                -- 0-100 score
    sentiment_polarity FLOAT,              -- -1.0 to 1.0
    sentiment_label TEXT,                  -- 'positive', 'negative', 'neutral'
    posts BIGINT,                          -- Number of posts/videos found
    views BIGINT,                          -- Total views (if applicable)
    likes BIGINT,                          -- Total likes (if applicable)
    comments BIGINT,                       -- Total comments (if applicable)
    language TEXT,                         -- Detected language (en, es, etc.) - kept for compatibility
    metadata JSONB,                        -- Platform-specific metadata (video IDs, channels, etc.)
    version_id UUID,                       -- Batch ID for grouping inserts
    scraped_at TIMESTAMPTZ DEFAULT NOW(),  -- Timestamp of scraping
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by platform and time
CREATE INDEX IF NOT EXISTS idx_youtube_platform_time ON public.youtube (platform, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_youtube_version ON public.youtube (version_id);

-- Create scraping logs table
CREATE TABLE IF NOT EXISTS public.scraping_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    status TEXT NOT NULL,                  -- 'success', 'failure'
    items_collected INTEGER,
    error_message TEXT,
    duration_seconds FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
