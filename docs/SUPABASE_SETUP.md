# Supabase Integration Setup

## Overview

The LinkedIn scraper now supports saving data directly to Supabase database. This enables:
- Persistent storage of hashtag data
- Historical tracking of trending hashtags
- Query capabilities for analytics
- Integration with other applications

## Database Schema

The scraper uses the `linkedin` table (designed for multi-platform support). The schema includes:

```sql
CREATE TABLE public.linkedin (
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
    sentiment_label = ANY(ARRAY['positive'::text, 'negative'::text, 'neutral'::text])
  )
);
```

## Setup Instructions

### 1. Create Supabase Table

Run this SQL in your Supabase SQL Editor:

```sql
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
    sentiment_label = ANY(ARRAY['positive'::text, 'negative'::text, 'neutral'::text])
  )
) TABLESPACE pg_default;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_linkedin_platform 
  ON public.linkedin USING btree (platform);

CREATE INDEX IF NOT EXISTS idx_linkedin_hashtag 
  ON public.linkedin USING btree (topic_hashtag);

CREATE INDEX IF NOT EXISTS idx_linkedin_scraped_at 
  ON public.linkedin USING btree (scraped_at);

CREATE INDEX IF NOT EXISTS idx_linkedin_version_id 
  ON public.linkedin USING btree (version_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_sentiment 
  ON public.linkedin USING btree (sentiment_label);

CREATE INDEX IF NOT EXISTS idx_linkedin_metadata 
  ON public.linkedin USING gin (metadata);

-- 4. Create Scrape Logs Table (Required for run tracking)
CREATE TABLE IF NOT EXISTS public.scrape_logs (
  id bigserial NOT NULL,
  platform text NOT NULL,
  started_at timestamp with time zone NOT NULL DEFAULT now(),
  ended_at timestamp with time zone NULL,
  status text NOT NULL,
  error text NULL,
  proxy_used text NULL,
  records_inserted integer NULL DEFAULT 0,
  version_id uuid NOT NULL,
  metadata jsonb NULL,
  CONSTRAINT scrape_logs_pkey PRIMARY KEY (id),
  CONSTRAINT scrape_logs_status_check CHECK (
    status = ANY (ARRAY['running'::text, 'success'::text, 'failed'::text, 'interrupted'::text])
  )
) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_scrape_logs_started_at 
  ON public.scrape_logs USING btree (started_at DESC);
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
USE_SUPABASE=true
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the `supabase` package.

### 4. Run the Scraper

The scraper will automatically:
- Connect to Supabase on startup
- Save all top hashtags to the database
- Include metadata about the scraping session

## Data Structure

Each hashtag record includes:

- **platform**: "linkedin"
- **topic_hashtag**: The hashtag (e.g., "#codingninjas")
- **engagement_score**: Calculated as (count / total) * 100
- **sentiment_polarity**: Currently 0.0 (neutral) - can be enhanced
- **sentiment_label**: "neutral" (can be enhanced)
- **posts**: Number of occurrences
- **views**: NULL (not available from scraping)
- **metadata**: JSON object with:
  - total_occurrences
  - total_hashtags_collected
  - unique_hashtags
  - percentage
  - scraped_from: "linkedin_feed"
  - session_id: unique version ID
- **scraped_at**: Timestamp of when data was scraped
- **version_id**: Unique ID for this scraping session

## Querying Data

### Get Latest Hashtags

```sql
SELECT * 
FROM linkedin 
WHERE platform = 'linkedin' 
ORDER BY scraped_at DESC 
LIMIT 10;
```

### Get Trending Hashtags by Engagement

```sql
SELECT topic_hashtag, engagement_score, posts, scraped_at
FROM linkedin 
WHERE platform = 'linkedin' 
ORDER BY engagement_score DESC 
LIMIT 10;
```

### Get Hashtags by Date Range

```sql
SELECT topic_hashtag, posts, scraped_at
FROM linkedin 
WHERE platform = 'linkedin' 
  AND scraped_at >= NOW() - INTERVAL '7 days'
ORDER BY posts DESC;
```

### Get All Hashtags from a Session

```sql
SELECT * 
FROM linkedin 
WHERE version_id = 'your-version-id-here'
ORDER BY engagement_score DESC;
```

## Disabling Supabase

To disable Supabase storage:

1. Set in `.env`:
```env
USE_SUPABASE=false
```

2. Or remove Supabase credentials - the scraper will continue without it and only save to JSON.

## Troubleshooting

### Error: "Supabase credentials not found"
- Make sure `.env` file exists in project root
- Check that `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
- Verify credentials are correct

### Error: "Error inserting data to Supabase"
- Check table exists in Supabase
- Verify table schema matches expected format
- Check RLS (Row Level Security) policies allow inserts
- Ensure anon key has insert permissions

### Error: "Table 'linkedin' does not exist"
- Run the SQL schema creation script in Supabase SQL Editor
- Verify table name is correct (case-sensitive)

## Security Notes

- The anon key is safe to use in client-side code
- For production, consider using service role key for server-side operations
- Implement RLS policies to control data access
- Never commit `.env` file to version control

## Next Steps

- Add sentiment analysis to calculate real sentiment scores
- Implement data aggregation for historical trends
- Create dashboard to visualize trending hashtags
- Add scheduled scraping jobs
- Implement data retention policies

