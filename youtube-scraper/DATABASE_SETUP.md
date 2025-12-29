# Supabase Database Setup Guide - Sprint-1 Edition

This scraper uses Supabase for data storage with the **`youtube` table** schema.

## Features

- ✅ Supabase storage with `youtube` table
- ✅ TextBlob sentiment analysis (polarity and label)
- ✅ Engagement score calculation based on views, likes, and comments
- ✅ Video metadata collection (views, likes, comments, titles, descriptions)
- ✅ Batch insertion with retry logic for reliability
- ✅ Scraping logs for monitoring

---

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
python -m textblob.download_corpora  # First time only
```

### 2. Configure Environment

Add to your `.env` file:

```env
# Supabase (Required)
USE_DATABASE=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here

# YouTube API (Required)
YOUTUBE_API_KEY=your_youtube_api_key

# Proxy (Sprint-1 Requirement)
PROXY_LIST=http://proxy1:port,http://proxy2:port
PROXY_STRICT_MODE=true
```

### 3. Create Database Tables

Go to **Supabase Dashboard → SQL Editor** and run:

```sql
-- Create youtube table
CREATE TABLE IF NOT EXISTS public.youtube (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,
  topic_hashtag TEXT NOT NULL,
  engagement_score DOUBLE PRECISION,
  sentiment_polarity DOUBLE PRECISION,
  sentiment_label TEXT CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
  posts BIGINT,
  views BIGINT,
  likes BIGINT,
  comments BIGINT,
  metadata JSONB,
  scraped_at TIMESTAMPTZ DEFAULT NOW(),
  version_id UUID NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_youtube_platform ON public.youtube(platform);
CREATE INDEX IF NOT EXISTS idx_youtube_hashtag ON public.youtube(topic_hashtag);
CREATE INDEX IF NOT EXISTS idx_youtube_scraped_at ON public.youtube(scraped_at);
CREATE INDEX IF NOT EXISTS idx_youtube_version_id ON public.youtube(version_id);
CREATE INDEX IF NOT EXISTS idx_youtube_sentiment ON public.youtube(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_youtube_metadata ON public.youtube USING GIN(metadata);

-- Create scraping logs table
CREATE TABLE IF NOT EXISTS public.scraping_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    items_collected INTEGER,
    error_message TEXT,
    duration_seconds FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Run the Scraper

```bash
python main.py --locales US --limit 10
```

---

## Database Schema

### `youtube` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGSERIAL | Primary key |
| `platform` | TEXT | Platform name (always "youtube") |
| `topic_hashtag` | TEXT | The trending hashtag |
| `engagement_score` | DOUBLE PRECISION | Calculated score (0-100) |
| `sentiment_polarity` | DOUBLE PRECISION | Sentiment score (-1.0 to 1.0) |
| `sentiment_label` | TEXT | 'positive', 'negative', or 'neutral' |
| `posts` | BIGINT | Number of videos with this hashtag |
| `views` | BIGINT | Average views per video |
| `likes` | BIGINT | Total likes across videos |
| `comments` | BIGINT | Total comments across videos |
| `metadata` | JSONB | Additional data (video IDs, channels, etc.) |
| `scraped_at` | TIMESTAMPTZ | When data was collected |
| `version_id` | UUID | Batch identifier for grouping |

### `scraping_logs` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `platform` | TEXT | Platform name |
| `status` | TEXT | 'success', 'failure', etc. |
| `items_collected` | INTEGER | Number of items scraped |
| `error_message` | TEXT | Error details if failed |
| `duration_seconds` | FLOAT | How long scraping took |
| `metadata` | JSONB | Additional context |
| `created_at` | TIMESTAMPTZ | Log timestamp |

---

## How It Works

### 1. Data Collection
- Scraper fetches trending videos via YouTube API
- Extracts hashtags from video pages using Playwright
- Collects metadata: views, likes, comments, titles, descriptions

### 2. Processing
- **Engagement Score**: Calculated from views, likes, and frequency
  ```
  views_score = log10(avg_views + 1) * 10
  frequency_score = min(count * 5, 50)
  engagement_score = min(views_score + frequency_score, 100.0)
  ```

- **Sentiment Analysis**: TextBlob analyzes video titles/descriptions
  - Polarity: -1.0 (negative) to 1.0 (positive)
  - Label: 'positive', 'negative', or 'neutral'

### 3. Storage
- Batch insertion to Supabase `youtube` table
- Retry logic with exponential backoff
- Scraping execution logged to `scraping_logs` table

---

## Usage Examples

### With Database Storage (Default)

```bash
# Set in .env: USE_DATABASE=true
python main.py --locales US,IN --limit 50
```

### Without Database Storage

```bash
# Set in .env: USE_DATABASE=false
python main.py --locales US --limit 50
```

### Test Database Connection

```bash
python tests\check_config.py
```

### Run Integration Tests

```bash
python tests\test_db_integration.py
```

---

## Troubleshooting

### ❌ "Database connection failed"

**Cause**: Invalid credentials or network issue

**Solution**:
1. Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`
2. Check your Supabase project is active
3. Test connection: `python tests\check_config.py`

### ❌ "Table 'youtube' does not exist"

**Cause**: Database tables not created

**Solution**:
1. Go to Supabase Dashboard → SQL Editor
2. Run the SQL from step 3 above
3. Verify table exists in Table Editor

### ❌ "Column 'likes' does not exist"

**Cause**: Old table schema missing new columns

**Solution**:
```sql
ALTER TABLE public.youtube 
ADD COLUMN IF NOT EXISTS likes BIGINT,
ADD COLUMN IF NOT EXISTS comments BIGINT;
```

### ❌ "RLS policy violation"

**Cause**: Row Level Security blocking inserts

**Solution**:
1. Go to Supabase Dashboard → Authentication → Policies
2. Disable RLS for `youtube` table OR
3. Create policy allowing anonymous inserts

### ⚠️ TextBlob sentiment analysis error

**Solution**:
```bash
python -m textblob.download_corpora
```

---

## Monitoring

### View Recent Data

```sql
SELECT 
  topic_hashtag,
  engagement_score,
  sentiment_label,
  posts,
  views,
  scraped_at
FROM public.youtube
ORDER BY scraped_at DESC
LIMIT 20;
```

### Check Scraping Logs

```sql
SELECT 
  platform,
  status,
  items_collected,
  duration_seconds,
  created_at
FROM public.scraping_logs
ORDER BY created_at DESC
LIMIT 10;
```

### Top Trending Hashtags

```sql
SELECT 
  topic_hashtag,
  engagement_score,
  sentiment_label,
  posts,
  views
FROM public.youtube
WHERE scraped_at > NOW() - INTERVAL '7 days'
ORDER BY engagement_score DESC
LIMIT 10;
```

---

## Best Practices

1. **Enable Database Storage**: Set `USE_DATABASE=true` for production
2. **Monitor Logs**: Check `scraping_logs` table regularly
3. **Clean Old Data**: Archive or delete old records periodically
4. **Use Indexes**: The provided indexes optimize common queries
5. **Backup Data**: Use Supabase backup features

---

## Example Output

```
INFO: Initializing proxy rotator (strict_mode=True)...
INFO: ProxyRotator initialized with 3 proxies (strict_mode=True)
INFO: Database connection verified (table: youtube)
INFO: Fetching trending videos via API (region: US)...
INFO: Processing 10 videos with Playwright...
INFO: Analyzing hashtags (sentiment & engagement)...
INFO: Storing 15 hashtag records in Supabase...
SUCCESS: Database storage completed
```

---

## Need Help?

- Check `tests\check_config.py` for configuration issues
- Run `tests\test_db_integration.py` for database connectivity
- Review Supabase logs in dashboard
- Ensure all environment variables are set correctly
