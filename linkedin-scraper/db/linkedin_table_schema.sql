-- LinkedIn Hashtags Scraper - Supabase Table Schema
-- This schema matches the Instagram table structure
-- Run this SQL in your Supabase SQL Editor

-- Create the linkedin table
CREATE TABLE IF NOT EXISTS public.linkedin (
  id bigserial NOT NULL,
  platform text NOT NULL,
  topic_hashtag text NOT NULL,
  engagement_score double precision NULL,
  sentiment_polarity double precision NULL,
  sentiment_label text NULL,
  posts bigint NULL,
  views bigint NULL,
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

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.linkedin TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE linkedin_id_seq TO anon, authenticated;

