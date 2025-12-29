-- Create tiktok table with all required columns and indexes
-- Migration: 002_create_tiktok_table.sql

-- Drop table if exists (use with caution in production)
-- DROP TABLE IF EXISTS public.tiktok CASCADE;

-- Create main table
CREATE TABLE IF NOT EXISTS public.tiktok (
  id BIGSERIAL NOT NULL,
  platform TEXT NOT NULL,
  topic TEXT NOT NULL,
  engagement_score DOUBLE PRECISION NULL,
  sentiment_polarity DOUBLE PRECISION NULL,
  sentiment_label TEXT NULL,
  posts BIGINT NULL,
  views BIGINT NULL,
  metadata JSONB NULL,
  scraped_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
  version_id UUID NULL,
  collected_at_hour TIMESTAMP WITH TIME ZONE NULL,
  CONSTRAINT tiktok_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Add unique constraint for hourly deduplication
ALTER TABLE public.tiktok 
DROP CONSTRAINT IF EXISTS uq_tiktok_topic_hour;

ALTER TABLE public.tiktok 
ADD CONSTRAINT uq_tiktok_topic_hour 
UNIQUE (topic, collected_at_hour);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tiktok_platform 
ON public.tiktok USING BTREE (platform) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_tiktok_scraped_at 
ON public.tiktok USING BTREE (scraped_at) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_tiktok_version_id 
ON public.tiktok USING BTREE (version_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_tiktok_topic 
ON public.tiktok USING BTREE (topic) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_tiktok_engagement_score 
ON public.tiktok USING BTREE (engagement_score DESC) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_tiktok_topic_collected_at_hour 
ON public.tiktok USING BTREE (topic, collected_at_hour) TABLESPACE pg_default;

-- Add comment to table
COMMENT ON TABLE public.tiktok IS 'TikTok trending hashtags with engagement metrics and sentiment analysis';

-- Add column comments
COMMENT ON COLUMN public.tiktok.platform IS 'Social media platform (TikTok)';
COMMENT ON COLUMN public.tiktok.topic IS 'Hashtag name including # symbol';
COMMENT ON COLUMN public.tiktok.engagement_score IS 'Calculated engagement score (1.0-10.0)';
COMMENT ON COLUMN public.tiktok.sentiment_polarity IS 'Sentiment polarity (-1.0 to 1.0)';
COMMENT ON COLUMN public.tiktok.sentiment_label IS 'Sentiment label (Positive/Neutral/Negative)';
COMMENT ON COLUMN public.tiktok.posts IS 'Number of posts using this hashtag';
COMMENT ON COLUMN public.tiktok.views IS 'Total views for this hashtag';
COMMENT ON COLUMN public.tiktok.metadata IS 'Additional metadata (rank, category, source_url)';
COMMENT ON COLUMN public.tiktok.scraped_at IS 'Timestamp when data was scraped';
COMMENT ON COLUMN public.tiktok.collected_at_hour IS 'Hour bucket for deduplication (truncated to hour)';
COMMENT ON COLUMN public.tiktok.version_id IS 'Scraper run session ID (UUID)';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON public.tiktok TO authenticated;
-- GRANT USAGE, SELECT ON SEQUENCE public.tiktok_id_seq TO authenticated;
