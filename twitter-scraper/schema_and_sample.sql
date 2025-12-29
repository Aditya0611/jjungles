-- Exact Schema provided by User
-- WARNING: This will RESET the table.

DROP TABLE IF EXISTS twitter;

create table public.twitter (
  id bigserial not null,
  platform text not null,
  topic_hashtag text not null,
  engagement_score double precision null default 0,
  sentiment_polarity double precision null default 0,
  sentiment_label text null default 'Neutral'::text,
  posts bigint null default 0,
  views bigint null default 0,
  metadata jsonb null default '{}'::jsonb,
  scraped_at timestamp with time zone null default now(),
  version_id uuid null default gen_random_uuid (),
  language text null,
  retweets bigint null default 0,
  likes bigint null default 0,
  first_seen timestamp with time zone null,
  last_seen timestamp with time zone null,
  constraint twitter_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_twitter_platform on public.twitter using btree (platform) TABLESPACE pg_default;
create index IF not exists idx_twitter_scraped_at on public.twitter using btree (scraped_at desc) TABLESPACE pg_default;
create index IF not exists idx_twitter_version_id on public.twitter using btree (version_id) TABLESPACE pg_default;
create index IF not exists idx_twitter_engagement on public.twitter using btree (engagement_score desc) TABLESPACE pg_default;
create index IF not exists idx_twitter_hashtag on public.twitter using btree (platform, topic_hashtag) TABLESPACE pg_default;

-- Logs Table
CREATE TABLE IF NOT EXISTS scraping_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scraper_name TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    end_time TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'running', -- running, success, failed
    items_scraped INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_scraping_logs_scraper_time ON scraping_logs(scraper_name, start_time DESC);
