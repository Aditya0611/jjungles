-- LEGACY SCHEMA FOR INSTAGRAM TABLE (USER REQUESTED)
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.instagram (
  id bigserial not null,
  platform text not null,
  topic_hashtag text not null,
  engagement_score double precision null,
  sentiment_polarity double precision null,
  sentiment_label text null,
  posts bigint null,
  views bigint null,
  metadata jsonb null,
  scraped_at timestamp with time zone null default now(),
  version_id uuid not null,
  constraint instagram_pkey primary key (id),
  constraint instagram_sentiment_label_check check (
    (
      sentiment_label = any (
        array[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_instagram_platform on public.instagram using btree (platform);
CREATE INDEX IF NOT EXISTS idx_instagram_hashtag on public.instagram using btree (topic_hashtag);
CREATE INDEX IF NOT EXISTS idx_instagram_scraped_at on public.instagram using btree (scraped_at);
CREATE INDEX IF NOT EXISTS idx_instagram_version_id on public.instagram using btree (version_id);
CREATE INDEX IF NOT EXISTS idx_instagram_sentiment on public.instagram using btree (sentiment_label);
CREATE INDEX IF NOT EXISTS idx_instagram_metadata on public.instagram using gin (metadata);
