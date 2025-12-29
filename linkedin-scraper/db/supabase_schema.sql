-- LinkedIn Hashtags Scraper - Supabase Table Schema (FULL VERSION)
-- 
-- ⚠️ DEPRECATION NOTICE:
-- This schema creates a platform-specific 'linkedin' table.
-- For new installations, use 'unified_trends_schema.sql' instead,
-- which creates a unified 'trends' table supporting all platforms.
-- 
-- This file is kept for backward compatibility reference only.
-- 
-- Run this SQL in your Supabase SQL Editor to create/update the table with all fields

-- Drop existing table if you want to recreate (CAUTION: This will delete all data)
-- DROP TABLE IF EXISTS public.linkedin CASCADE;

-- Create the linkedin table with ALL fields for complete data storage
CREATE TABLE IF NOT EXISTS public.linkedin (
  id bigserial NOT NULL,
  platform text NOT NULL,
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
  CONSTRAINT linkedin_pkey PRIMARY KEY (id),
  CONSTRAINT linkedin_sentiment_label_check CHECK (
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
  CONSTRAINT linkedin_sentiment_textblob_label_check CHECK (
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
  CONSTRAINT linkedin_sentiment_vader_label_check CHECK (
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
  CONSTRAINT linkedin_sentiment_transformer_label_check CHECK (
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
  CONSTRAINT linkedin_sentiment_consensus_label_check CHECK (
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
CREATE INDEX IF NOT EXISTS idx_linkedin_platform 
  ON public.linkedin USING btree (platform) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_hashtag 
  ON public.linkedin USING btree (topic_hashtag) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_scraped_at 
  ON public.linkedin USING btree (scraped_at) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_version_id 
  ON public.linkedin USING btree (version_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_sentiment 
  ON public.linkedin USING btree (sentiment_label) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_metadata 
  ON public.linkedin USING gin (metadata) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_language 
  ON public.linkedin USING btree (language) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_sentiment_consensus 
  ON public.linkedin USING btree (sentiment_consensus_label) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_sentiment_scores 
  ON public.linkedin USING gin (sentiment_scores) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_linkedin_engagement_score 
  ON public.linkedin USING btree (engagement_score) TABLESPACE pg_default;

-- Add missing columns if table already exists (ALTER TABLE statements)
-- Run these if you're updating an existing table instead of recreating

DO $$ 
BEGIN
  -- Add sentiment_textblob_polarity if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_textblob_polarity') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_textblob_polarity double precision NULL;
  END IF;

  -- Add sentiment_textblob_label if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_textblob_label') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_textblob_label text NULL;
  END IF;

  -- Add sentiment_vader_compound if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_vader_compound') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_vader_compound double precision NULL;
  END IF;

  -- Add sentiment_vader_label if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_vader_label') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_vader_label text NULL;
  END IF;

  -- Add sentiment_transformer_score if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_transformer_score') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_transformer_score double precision NULL;
  END IF;

  -- Add sentiment_transformer_label if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_transformer_label') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_transformer_label text NULL;
  END IF;

  -- Add sentiment_consensus_label if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_consensus_label') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_consensus_label text NULL;
  END IF;

  -- Add sentiment_average_score if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_average_score') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_average_score double precision NULL;
  END IF;

  -- Add sentiment_scores if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'sentiment_scores') THEN
    ALTER TABLE public.linkedin ADD COLUMN sentiment_scores jsonb NULL;
  END IF;

  -- Add caption if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'caption') THEN
    ALTER TABLE public.linkedin ADD COLUMN caption text NULL;
  END IF;

  -- Add language if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'language') THEN
    ALTER TABLE public.linkedin ADD COLUMN language text NULL;
  END IF;

  -- Add language_confidence if it doesn't exist
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'language_confidence') THEN
    ALTER TABLE public.linkedin ADD COLUMN language_confidence double precision NULL;
  END IF;
END $$;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.linkedin TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE linkedin_id_seq TO anon, authenticated;

-- Enable Row Level Security (RLS) - Optional but recommended
-- ALTER TABLE public.linkedin ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow anonymous inserts (if using anon key)
-- Adjust this based on your security requirements
-- CREATE POLICY "Allow anonymous inserts" ON public.linkedin
--   FOR INSERT
--   TO anon
--   WITH CHECK (true);

-- Create a policy to allow authenticated users to read
-- CREATE POLICY "Allow authenticated reads" ON public.linkedin
--   FOR SELECT
--   TO authenticated
--   USING (true);

-- Create scrape_logs table for persisting application logs
CREATE TABLE IF NOT EXISTS public.scrape_logs (
  id bigserial NOT NULL,
  timestamp timestamp with time zone DEFAULT now(),
  level text NOT NULL,
  message text NOT NULL,
  context jsonb NULL,
  CONSTRAINT scrape_logs_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_scrape_logs_timestamp 
  ON public.scrape_logs USING btree (timestamp) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_scrape_logs_level 
  ON public.scrape_logs USING btree (level) TABLESPACE pg_default;
