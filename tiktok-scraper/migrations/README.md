# Database Setup

This folder contains the SQL schema for creating the database table.

## Quick Setup

1. Go to your Supabase project: https://supabase.com/dashboard
2. Click **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy and paste the contents of `002_create_tiktok_table.sql`
5. Click **Run** (bottom right)
6. Verify table exists in **Table Editor**

## Schema Overview

The `tiktok` table stores trending hashtag data with these columns:

- **id** - Auto-incrementing primary key
- **platform** - Social media platform (always "TikTok")
- **topic** - Hashtag name (e.g., "#viral")
- **engagement_score** - Calculated score from 1.0 to 10.0
- **sentiment_polarity** - Sentiment score from -1.0 to 1.0
- **sentiment_label** - "Positive", "Neutral", or "Negative"
- **posts** - Number of posts using this hashtag
- **views** - Total views for this hashtag
- **metadata** - JSON with additional info (rank, category, source URL)
- **scraped_at** - Timestamp when data was collected
- **version_id** - UUID to group hashtags from same scrape run

## Indexes Created

For optimal query performance:
- `idx_tiktok_platform` - Filter by platform
- `idx_tiktok_scraped_at` - Sort by time
- `idx_tiktok_version_id` - Group by scrape session
- `idx_tiktok_topic` - Search by hashtag

## Important: Disable RLS

After creating the table, disable Row Level Security:

```sql
ALTER TABLE public.tiktok DISABLE ROW LEVEL SECURITY;
```

This allows the scraper to read/write data without authentication issues.

## Verify Setup

Run this query to confirm everything works:

```sql
-- Should return 0 initially
SELECT COUNT(*) FROM public.tiktok;

-- After first scrape, should show your data
SELECT * FROM public.tiktok ORDER BY scraped_at DESC LIMIT 10;
```

## Troubleshooting

**Error: "table already exists"**
- Table was already created. You can skip this step or drop and recreate:
```sql
DROP TABLE IF EXISTS public.tiktok CASCADE;
-- Then run 002_create_tiktok_table.sql again
```

**Error: "permission denied"**
- Make sure you're logged into Supabase as project owner
- Check that you're in the correct project

**No data showing after scrape**
- Disable RLS: `ALTER TABLE public.tiktok DISABLE ROW LEVEL SECURITY;`
- Check connection: Verify SUPABASE_URL and SUPABASE_KEY are set

For more help, see the main README.md file.
