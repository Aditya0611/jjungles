-- Unified Trends Table Schema for Cross-Platform Hashtag Scraping
-- This table supports all platforms: LinkedIn, Twitter, Instagram, TikTok, Facebook
-- Run this SQL in your Supabase SQL Editor to create the unified trends table

-- Create the unified trends table with platform-agnostic schema
CREATE TABLE IF NOT EXISTS public.trends (
  id bigserial NOT NULL,
  platform text NOT NULL,  -- Platform identifier: 'linkedin', 'twitter', 'instagram', 'tiktok', 'facebook'
  topic_hashtag text NOT NULL,
  engagement_score double precision NULL,
  sentiment_polarity double precision NULL,
  sentiment_label text NULL,
  -- All three sentiment analysis methods
  sentiment_textblob_polarity double precision NULL,
  sentiment_textblob_label text NULL,
  sentiment_vader_compound double precision NULL,
  sentiment_vader_label text NULL,
  sentiment_transformer_score double precision NULL,
  sentiment_transformer_label text NULL,
  sentiment_consensus_label text NULL,
  sentiment_average_score double precision NULL,
  sentiment_scores jsonb NULL,
  -- Language detection
  caption text NULL,
  language text NULL,
  language_confidence double precision NULL,
  -- Engagement metrics
  posts bigint NULL,
  views bigint NULL,
  -- Metadata and tracking
  metadata jsonb NULL,
  scraped_at timestamp with time zone NULL DEFAULT now(),
  version_id uuid NOT NULL,
  CONSTRAINT trends_pkey PRIMARY KEY (id),
  CONSTRAINT trends_sentiment_label_check CHECK (
    (
      sentiment_label = ANY (
        ARRAY[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      )
    )
  ),
  CONSTRAINT trends_sentiment_textblob_label_check CHECK (
    (
      sentiment_textblob_label = ANY (
        ARRAY[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      ) OR sentiment_textblob_label IS NULL
    )
  ),
  CONSTRAINT trends_sentiment_vader_label_check CHECK (
    (
      sentiment_vader_label = ANY (
        ARRAY[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      ) OR sentiment_vader_label IS NULL
    )
  ),
  CONSTRAINT trends_sentiment_transformer_label_check CHECK (
    (
      sentiment_transformer_label = ANY (
        ARRAY[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      ) OR sentiment_transformer_label IS NULL
    )
  ),
  CONSTRAINT trends_sentiment_consensus_label_check CHECK (
    (
      sentiment_consensus_label = ANY (
        ARRAY[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      ) OR sentiment_consensus_label IS NULL
    )
  )
) TABLESPACE pg_default;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trends_platform 
  ON public.trends USING btree (platform) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_hashtag 
  ON public.trends USING btree (topic_hashtag) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_scraped_at 
  ON public.trends USING btree (scraped_at) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_version_id 
  ON public.trends USING btree (version_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_sentiment 
  ON public.trends USING btree (sentiment_label) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_metadata 
  ON public.trends USING gin (metadata) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_language 
  ON public.trends USING btree (language) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_sentiment_consensus 
  ON public.trends USING btree (sentiment_consensus_label) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_sentiment_scores 
  ON public.trends USING gin (sentiment_scores) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_trends_engagement_score 
  ON public.trends USING btree (engagement_score) TABLESPACE pg_default;

-- Composite index for common queries (platform + scraped_at)
CREATE INDEX IF NOT EXISTS idx_trends_platform_scraped_at 
  ON public.trends USING btree (platform, scraped_at DESC) TABLESPACE pg_default;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.trends TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE trends_id_seq TO anon, authenticated;

-- ============================================================================
-- Scrape Logs Table for Run Tracking
-- ============================================================================

-- Create scrape_logs table for persisting scraping run metadata
CREATE TABLE IF NOT EXISTS public.scrape_logs (
  id bigserial NOT NULL,
  platform text NOT NULL,  -- Platform identifier: 'linkedin', 'twitter', etc.
  started_at timestamp with time zone NOT NULL DEFAULT now(),
  ended_at timestamp with time zone NULL,
  status text NOT NULL,  -- 'running', 'success', 'failed', 'interrupted'
  error text NULL,  -- Error message if status is 'failed'
  proxy_used text NULL,  -- Proxy server used (if any)
  records_inserted integer NULL DEFAULT 0,  -- Number of records inserted
  version_id uuid NOT NULL,  -- Links to trends.version_id
  metadata jsonb NULL,  -- Additional run metadata (scrolls, posts processed, etc.)
  CONSTRAINT scrape_logs_pkey PRIMARY KEY (id),
  CONSTRAINT scrape_logs_status_check CHECK (
    status = ANY (ARRAY['running'::text, 'success'::text, 'failed'::text, 'interrupted'::text])
  )
) TABLESPACE pg_default;

-- Create indexes for scrape_logs
CREATE INDEX IF NOT EXISTS idx_scrape_logs_platform 
  ON public.scrape_logs USING btree (platform) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_scrape_logs_started_at 
  ON public.scrape_logs USING btree (started_at DESC) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_scrape_logs_status 
  ON public.scrape_logs USING btree (status) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_scrape_logs_version_id 
  ON public.scrape_logs USING btree (version_id) TABLESPACE pg_default;

-- Grant permissions for scrape_logs
GRANT ALL ON public.scrape_logs TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE scrape_logs_id_seq TO anon, authenticated;

-- Enable Row Level Security (RLS) - Optional but recommended
-- ALTER TABLE public.trends ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow anonymous inserts (if using anon key)
-- Adjust this based on your security requirements
-- CREATE POLICY "Allow anonymous inserts" ON public.trends
--   FOR INSERT
--   TO anon
--   WITH CHECK (true);

-- Create a policy to allow authenticated users to read
-- CREATE POLICY "Allow authenticated reads" ON public.trends
--   FOR SELECT
--   TO authenticated
--   USING (true);

-- ============================================================================
-- OPTIONAL: Data Migration from linkedin table to trends table
-- ============================================================================
-- Uncomment the following section if you want to migrate existing data
-- from the platform-specific 'linkedin' table to the unified 'trends' table

/*
-- Migrate data from linkedin table to trends table
INSERT INTO public.trends (
  platform,
  topic_hashtag,
  engagement_score,
  sentiment_polarity,
  sentiment_label,
  sentiment_textblob_polarity,
  sentiment_textblob_label,
  sentiment_vader_compound,
  sentiment_vader_label,
  sentiment_transformer_score,
  sentiment_transformer_label,
  sentiment_consensus_label,
  sentiment_average_score,
  sentiment_scores,
  caption,
  language,
  language_confidence,
  posts,
  views,
  metadata,
  scraped_at,
  version_id
)
SELECT 
  'linkedin' as platform,  -- Set platform to 'linkedin' for all migrated records
  topic_hashtag,
  engagement_score,
  sentiment_polarity,
  sentiment_label,
  sentiment_textblob_polarity,
  sentiment_textblob_label,
  sentiment_vader_compound,
  sentiment_vader_label,
  sentiment_transformer_score,
  sentiment_transformer_label,
  sentiment_consensus_label,
  sentiment_average_score,
  sentiment_scores,
  caption,
  language,
  language_confidence,
  posts,
  views,
  metadata,
  scraped_at,
  version_id
FROM public.linkedin
WHERE NOT EXISTS (
  -- Avoid duplicates: only migrate records that don't already exist in trends
  SELECT 1 FROM public.trends t 
  WHERE t.platform = 'linkedin' 
    AND t.topic_hashtag = linkedin.topic_hashtag 
    AND t.version_id = linkedin.version_id
);

-- Verify migration
SELECT 
  'Migration Complete' as status,
  COUNT(*) as migrated_records
FROM public.trends
WHERE platform = 'linkedin';
*/

-- ============================================================================
-- Usage Examples
-- ============================================================================

-- View latest records from all platforms
-- SELECT 
--     platform,
--     topic_hashtag,
--     engagement_score,
--     sentiment_label,
--     posts,
--     scraped_at
-- FROM public.trends
-- ORDER BY scraped_at DESC
-- LIMIT 20;

-- View top hashtags by platform
-- SELECT 
--     platform,
--     topic_hashtag,
--     engagement_score,
--     sentiment_label,
--     posts
-- FROM public.trends
-- WHERE platform = 'linkedin'  -- Filter by specific platform
-- ORDER BY engagement_score DESC
-- LIMIT 10;

-- View cross-platform trending hashtags
-- SELECT 
--     topic_hashtag,
--     COUNT(DISTINCT platform) as platform_count,
--     SUM(posts) as total_posts,
--     AVG(engagement_score) as avg_engagement
-- FROM public.trends
-- WHERE scraped_at > NOW() - INTERVAL '7 days'
-- GROUP BY topic_hashtag
-- HAVING COUNT(DISTINCT platform) > 1  -- Hashtags trending on multiple platforms
-- ORDER BY platform_count DESC, total_posts DESC
-- LIMIT 20;
