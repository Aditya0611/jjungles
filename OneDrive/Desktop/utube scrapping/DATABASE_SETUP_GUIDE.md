# 🔧 Database Setup Issue - SOLUTION

## Problem Identified

✅ **Your credentials ARE configured correctly** in the `.env` file  
❌ **The database tables don't exist yet** in your Supabase project

**Error Message:**
```
APIError: 'trends' in the schema cache
```

This means the `trends` table hasn't been created in your Supabase database.

---

## Solution: Create Database Tables

### Option 1: Via Supabase Dashboard (Recommended)

1. **Open your Supabase project dashboard**
   - Go to https://supabase.com/dashboard
   - Select your project

2. **Navigate to SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Copy and paste this SQL**:

```sql
-- Create a unified table for storing trending topics/hashtags from all platforms
CREATE TABLE IF NOT EXISTS public.trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,                -- e.g., 'youtube', 'tiktok', 'twitter'
    topic_hashtag TEXT NOT NULL,           -- The trending topic or hashtag
    engagement_score FLOAT,                -- 0-100 score
    sentiment_polarity FLOAT,              -- -1.0 to 1.0
    sentiment_label TEXT,                  -- 'positive', 'negative', 'neutral'
    posts INTEGER,                         -- Number of posts/videos found
    views BIGINT,                          -- Total views (if applicable)
    likes BIGINT,                          -- Total likes (if applicable)
    comments BIGINT,                       -- Total comments (if applicable)
    language TEXT,                         -- Detected language (en, es, etc.)
    metadata JSONB,                        -- Platform-specific metadata (video IDs, channels, etc.)
    version_id UUID,                       -- Batch ID for grouping inserts
    scraped_at TIMESTAMPTZ DEFAULT NOW(),  -- Timestamp of scraping
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by platform and time
CREATE INDEX IF NOT EXISTS idx_trends_platform_time ON public.trends (platform, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_trends_version ON public.trends (version_id);

-- Create scraping logs table
CREATE TABLE IF NOT EXISTS public.scraping_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    status TEXT NOT NULL,                  -- 'success', 'failure'
    items_collected INTEGER,
    error_message TEXT,
    duration_seconds FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

4. **Click "Run"** to execute the SQL

5. **Verify tables were created**
   - Click on "Table Editor" in the left sidebar
   - You should see `trends` and `scraping_logs` tables

---

### Option 2: Use the SQL File

The SQL is already in your project at:
[`supabase_setup.sql`](file:///c:/Users/rajni/OneDrive/Desktop/utube%20scrapping/supabase_setup.sql)

Just copy the contents and paste into Supabase SQL Editor.

---

## After Creating Tables

Run the database test again:

```bash
python tests\test_db_integration.py
```

**Expected output:**
```
✅ PASSED: Database Connection
✅ PASSED: Schema Compatibility
✅ PASSED: Sample Data Insertion
✅ PASSED: Data Retrieval
✅ PASSED: Scraping Log

Total: 5/5 tests passed
🎉 ALL TESTS PASSED!
```

---

## Quick Verification

After creating the tables, run this to verify:

```bash
python tests\check_config.py
```

You should see:
```
✅ All required credentials are configured
✅ Database connection successful!
```

---

## Why This Happened

The scraper code is ready, but Supabase requires you to manually create tables via SQL. This is a one-time setup step that wasn't completed yet.

**This is NOT a bug** - it's standard Supabase workflow. The SQL file has been provided in your project since the beginning.

---

## Next Steps

1. ✅ Create tables in Supabase (follow steps above)
2. ✅ Run `python tests\test_db_integration.py` to verify
3. ✅ Run `python main.py --locales US --limit 5` to test full scraper
4. ✅ Check Supabase dashboard to see data inserted

---

**Need Help?** If you encounter any errors after running the SQL, let me know the exact error message.
