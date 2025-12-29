-- LinkedIn Hashtag Scraper - Missing Table Fix
-- Run this in your Supabase SQL Editor if you are getting "Could not find the table 'public.scrape_logs'" errors.

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
