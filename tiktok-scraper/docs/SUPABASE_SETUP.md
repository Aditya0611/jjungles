# Supabase Database Setup Guide

## Step 1: Create Supabase Project

1. Go to https://supabase.com/
2. Sign up or log in
3. Click "New Project"
4. Fill in:
   - **Project Name**: tiktok-scraper
   - **Database Password**: (save this securely)
   - **Region**: Choose closest to you
5. Click "Create new project" (takes ~2 minutes)

## Step 2: Get Your Credentials

Once project is created:

1. Go to **Project Settings** (gear icon)
2. Click **API** section
3. Copy these values:
   - **URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

## Step 3: Set Environment Variables

### Windows PowerShell
```powershell
# Set for current session
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your-anon-key-here"

# Verify
echo $env:SUPABASE_URL
echo $env:SUPABASE_KEY
```

### Make Permanent (Optional)
```powershell
# Add to PowerShell profile
notepad $PROFILE

# Add these lines:
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your-anon-key-here"
$env:PROXY_SERVER="your-proxy-url"  # Keep your proxy config too
```

## Step 4: Create Database Table

### Option A: Via Supabase Dashboard (Recommended)

1. Go to **SQL Editor** in Supabase dashboard
2. Click "New Query"
3. Copy and paste the contents of `migrations/002_create_tiktok_table.sql`
4. Click "Run" (bottom right)
5. Should see "Success. No rows returned"

### Option B: Via Command Line

```powershell
# Get your database connection string from Supabase
# Settings > Database > Connection string > URI

$DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres"

# Run migration
psql $DATABASE_URL -f migrations/002_create_tiktok_table.sql
```

### Option C: Manual Table Creation

If the SQL file doesn't work, create manually:

1. Go to **Table Editor** in Supabase
2. Click "New Table"
3. Name: `tiktok`
4. Add columns:
   - `id` - int8 (Primary Key, Auto-increment)
   - `platform` - text
   - `topic` - text
   - `engagement_score` - float8
   - `sentiment_polarity` - float8
   - `sentiment_label` - text
   - `posts` - int8
   - `views` - int8
   - `metadata` - jsonb
   - `scraped_at` - timestamptz (Default: now())
   - `collected_at_hour` - timestamptz
   - `version_id` - uuid

## Step 5: Verify Table Creation

Run this query in SQL Editor:

```sql
-- Check table exists
SELECT * FROM public.tiktok LIMIT 5;

-- Check indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename = 'tiktok';

-- Check constraints
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'public.tiktok'::regclass;
```

Expected indexes:
- `tiktok_pkey` (Primary Key)
- `idx_tiktok_platform`
- `idx_tiktok_scraped_at`
- `idx_tiktok_version_id`
- `idx_tiktok_topic`
- `idx_tiktok_engagement_score`
- `idx_tiktok_topic_collected_at_hour`
- `uq_tiktok_topic_hour` (Unique constraint)

## Step 6: Test the Scraper

```powershell
# Make sure both proxy and Supabase are configured
$env:PROXY_SERVER="your-proxy-url"
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your-anon-key"

# Run scraper
python base.py
```

Expected output:
```
============================================================
UPLOADING TOP 10 HASHTAGS TO SUPABASE
============================================================
Uploading top 10 hashtags (from 97 total) to Supabase
Upserting chunk 1/1 (10 records)
Successfully uploaded 10 records total
Upload successful!
```

## Step 7: View Your Data

### In Supabase Dashboard

1. Go to **Table Editor**
2. Select `tiktok` table
3. You should see your top 10 hashtags

### Via SQL Query

```sql
-- View all data
SELECT 
  topic,
  engagement_score,
  posts,
  scraped_at,
  metadata->>'rank' as rank
FROM public.tiktok
ORDER BY engagement_score DESC;

-- Count records
SELECT COUNT(*) FROM public.tiktok;

-- View latest scrape
SELECT 
  topic,
  engagement_score,
  posts
FROM public.tiktok
WHERE scraped_at > NOW() - INTERVAL '1 hour'
ORDER BY engagement_score DESC;
```

## Configuration Summary

**What the scraper does now:**
- ✅ Scrapes 50-200 hashtags from TikTok
- ✅ Calculates engagement scores (1-10)
- ✅ Sorts by engagement score (highest first)
- ✅ **Uploads only TOP 10 hashtags** to Supabase
- ✅ Deduplicates by (topic, collected_at_hour)
- ✅ Saves debug HTML locally for all hashtags

**Why only top 10?**
- Focused dataset of highest-value trends
- Reduces database storage costs
- Faster queries and analysis
- Easy to track top performers over time

**Want to upload more?** Edit `base.py`:
```python
# Line 835: Change top_n value
success = upload_to_supabase(supabase, scraped_data, "tiktok", version_id, top_n=50)
```

## Troubleshooting

### Error: "SUPABASE_URL or SUPABASE_KEY not set"

**Solution:**
```powershell
# Re-set environment variables
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your-anon-key"

# Verify they're set
echo $env:SUPABASE_URL
```

### Error: "Failed to upload to Supabase"

**Check:**
1. Credentials are correct
2. Table exists in Supabase
3. Internet connection is working
4. Supabase project is active (not paused)

**Test connection:**
```powershell
python -c "from supabase import create_client; import os; client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); print('Connected:', client)"
```

### Error: "duplicate key value violates unique constraint"

This is normal! The unique constraint prevents duplicate hashtags in the same hour.

**What happens:**
- First run: Inserts 10 hashtags ✅
- Second run (same hour): Updates existing hashtags ✅
- Next hour: Inserts new batch ✅

### Table doesn't exist

**Solution:**
```sql
-- Run this in Supabase SQL Editor
-- Copy/paste from migrations/002_create_tiktok_table.sql
CREATE TABLE IF NOT EXISTS public.tiktok (...);
```

## Advanced: Querying Trends

### Top hashtags from last 24 hours
```sql
SELECT 
  topic,
  AVG(engagement_score) as avg_score,
  COUNT(*) as appearances,
  MAX(posts) as max_posts
FROM public.tiktok
WHERE scraped_at > NOW() - INTERVAL '24 hours'
GROUP BY topic
ORDER BY avg_score DESC
LIMIT 10;
```

### Trend over time (hourly)
```sql
SELECT 
  topic,
  collected_at_hour,
  engagement_score,
  posts
FROM public.tiktok
WHERE topic = '#viral'
ORDER BY collected_at_hour DESC;
```

### Rising hashtags (not seen before)
```sql
WITH latest_run AS (
  SELECT MAX(scraped_at) as last_scrape FROM public.tiktok
)
SELECT t.topic, t.engagement_score, t.posts
FROM public.tiktok t, latest_run
WHERE t.scraped_at >= latest_run.last_scrape - INTERVAL '5 minutes'
  AND NOT EXISTS (
    SELECT 1 FROM public.tiktok t2
    WHERE t2.topic = t.topic
    AND t2.scraped_at < latest_run.last_scrape - INTERVAL '3 hours'
  )
ORDER BY t.engagement_score DESC;
```

## Cost & Limits

**Supabase Free Tier:**
- ✅ 500 MB database storage
- ✅ 2 GB bandwidth
- ✅ 50,000 monthly active users
- ✅ Unlimited API requests

**Estimated usage:**
- 10 hashtags/run × 8 runs/day = 80 new records/day
- ~2,400 records/month
- Storage: ~1-2 MB/month
- **Well within free tier!** 🎉

## Next Steps

1. ✅ Create Supabase project
2. ✅ Set environment variables
3. ✅ Run table migration
4. ✅ Test scraper with `python base.py`
5. ✅ View data in Supabase dashboard
6. 🔄 Schedule regular runs with GitHub Actions
7. 📊 Build dashboard/analytics on top of data

**Happy scraping!** 🚀
