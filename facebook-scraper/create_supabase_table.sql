-- ============================================================================
-- Supabase Table Schema for Facebook Hashtag Trends
-- ============================================================================
-- This matches your actual Supabase schema
-- Run this SQL in your Supabase SQL Editor if table doesn't exist
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.facebook (
  id BIGSERIAL NOT NULL,
  platform TEXT NOT NULL DEFAULT 'Facebook'::text,
  topic_hashtag TEXT NOT NULL,
  engagement_score DOUBLE PRECISION NULL,
  sentiment_polarity DOUBLE PRECISION NULL,
  sentiment_label TEXT NULL,
  posts BIGINT NULL,
  views BIGINT NULL,
  metadata JSONB NULL,
  scraped_at TIMESTAMPTZ NULL DEFAULT NOW(),
  version_id UUID NOT NULL,
  CONSTRAINT facebook_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Run tracking table
CREATE TABLE IF NOT EXISTS public.scrape_runs (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  end_time TIMESTAMPTZ NULL,
  status TEXT NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed'
  items_scraped INTEGER NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  metadata JSONB NULL,
  CONSTRAINT scrape_runs_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Granular scraping logs
CREATE TABLE IF NOT EXISTS public.scraping_log (
  id BIGSERIAL NOT NULL,
  run_id UUID NULL REFERENCES public.scrape_runs(id),
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT scraping_log_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_facebook_scraped_at ON public.facebook USING btree (scraped_at) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_facebook_version_id ON public.facebook USING btree (version_id) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_facebook_hashtag ON public.facebook USING btree (topic_hashtag) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_scrape_runs_platform ON public.scrape_runs USING btree (platform) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_scrape_runs_status ON public.scrape_runs USING btree (status) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_scraping_log_run_id ON public.scraping_log USING btree (run_id) TABLESPACE pg_default;

-- Enable Row Level Security (RLS)
ALTER TABLE public.facebook ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scrape_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scraping_log ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust based on your security needs)
CREATE POLICY "Allow all operations on facebook" ON public.facebook FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on scrape_runs" ON public.scrape_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on scraping_log" ON public.scraping_log FOR ALL USING (true) WITH CHECK (true);

-- Add comments
COMMENT ON TABLE public.facebook IS 'Stores Facebook hashtag trending data scraped by facebook_scraper';
COMMENT ON TABLE public.scrape_runs IS 'Tracks metadata for each scraping session';
COMMENT ON TABLE public.scraping_log IS 'Granular application logs for audit and debugging';
