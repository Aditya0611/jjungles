# TikTok Trend Scraper - Enterprise Edition

Professional social media trend extraction and analysis system with Odoo integration, automated scheduling, and cloud database persistence.

---

## 🎯 Features

- **Specialized TikTok Support** - Optimized for TikTok Creative Center trend extraction.
- **Advanced Web Scraping** - Playwright-based automation with stealth features and human-like behavior (currently optimized for TikTok).
- **Anti-Detection** - Stealth browser configuration, navigator overrides, and robust proxy rotation.
- **Automated Scheduling** - Built-in scheduler (APScheduler/Celery/RQ) with database-driven frequency management (0.5-24h).
- **Odoo Integration** - Seamless sync with Odoo module for dashboard visualization and admin control.
- **Smart Filtering** - Automatically identifies top trending hashtags based on engagement scores.
- **Cloud Integration** - Supabase database with indexed schema for high-performance analytics.
- **Sentiment Analysis** - VADER/TextBlob-based sentiment classification.
- **Trend Lifecycle Tracking** - Tracking `first_seen`, `peak_time`, `peak_score`, and decay rates.
- **Robust Error Handling** - Exponential backoff, persistent job queues, and automated retries.
- **Comprehensive Logging** - Structured JSON logging with trace context for production monitoring.


---

## 📋 Prerequisites

- Python 3.8+
- Windows/Linux/Mac
- Internet connection
- Supabase account (free tier available)
- Optional: Proxy service (for bypassing IP blocks)

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Step 2: Setup Supabase Database

1. Go to https://supabase.com and sign up (free)
2. Create a new project
3. Go to **SQL Editor** → **New Query**
4. Run the migrations in order:
   - Copy/paste content from `migrations/002_create_tiktok_table.sql` → Click **Run**
   - Copy/paste content from `migrations/003_add_trend_lifecycle_tracking.sql` → Click **Run**
   - Copy/paste content from `migrations/004_add_language_detection.sql` → Click **Run**
5. (Optional but recommended) Disable Row Level Security:
   ```sql
   ALTER TABLE public.tiktok DISABLE ROW LEVEL SECURITY;
   ```

### Step 3: Get Your Credentials

In Supabase dashboard:
1. Click **Project Settings** (gear icon)
2. Click **API** tab
3. Copy:
   - **URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGci...` (long string)

### Step 4: Set Environment Variables

#### Windows PowerShell:
```powershell
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your-anon-key-here"
```

#### Linux/Mac:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key-here"
```

#### Alternative: Create `.env` file
Create a `.env` file next to `base.py`:
```env
SUPABASE_URL=your_url_here
SUPABASE_KEY=your_key_here
```

### Step 5: Run! 🚀

```bash
python base.py
```

**Expected output:**
```
✅ Supabase client initialized successfully
✅ Scraped 93 unique hashtags
✅ Successfully uploaded 10 records total
```

### Step 6: View Your Data

Go to Supabase → **Table Editor** → **tiktok** table.

You should see 10 trending hashtags with:
- `topic`, `platform`
- `engagement_score`, `posts`, `views`
- `sentiment_polarity`, `sentiment_label`
- `language`, `language_confidence`
- `metadata.trend_lifecycle` (first_seen, peak_time, peak_score, is_decaying, decay_rate, trend_status)

---

## 📊 Output

### Console Output
```
============================================================
TIKTOK SCRAPER - Run ID: xxx-xxx-xxx
============================================================
✅ Scraped 93 unique hashtags
✅ Uploaded top 10 hashtags to Supabase
Duration: 6m 46s
============================================================

Sample results:
  1. #hoco - 156K Posts - Score: 7.8
  2. #sora - 95K Posts - Score: 7.7
  3. #homecoming - 62K Posts - Score: 7.4
  ...
```

### Database Output
Top 10 hashtags stored in Supabase `tiktok` table with:
- **Platform & Topic**: `platform` (TikTok), `topic`
- **Engagement & Sentiment**: `engagement_score` (1.0–10.0), `posts`, `views`, `sentiment_polarity`, `sentiment_label`
- **Language & Trend Lifecycle**: `language`, `language_confidence`, `metadata.trend_lifecycle`
- **Content Metadata**: `metadata.caption`, `metadata.title`, `metadata.post_format`, `metadata.sound`
- **Operational Fields**: `scraped_at`, `version_id`, `collected_at_hour`

---

## 🗄️ Detailed Database Setup

### Step 1: Create Supabase Project

1. Go to https://supabase.com/
2. Sign up or log in
3. Click "New Project"
4. Fill in:
   - **Project Name**: tiktok-scraper
   - **Database Password**: (save this securely)
   - **Region**: Choose closest to you
5. Click "Create new project" (takes ~2 minutes)

### Step 2: Run Database Migrations

Go to **SQL Editor** in Supabase dashboard and run these in order:

1. **Base Schema** (`migrations/002_create_tiktok_table.sql`)
   - Creates the main `tiktok` table
   - Sets up indexes for performance

2. **Trend Lifecycle** (`migrations/003_add_trend_lifecycle_tracking.sql`)
   - Adds trend lifecycle tracking columns
   - Enables first_seen, peak_time, decay analysis

3. **Language Detection** (`migrations/004_add_language_detection.sql`)
   - Adds language detection columns
   - Enables multi-language support

### Step 3: Disable Row Level Security (RLS)

After creating tables, disable RLS to allow the scraper to write data:

```sql
ALTER TABLE public.tiktok DISABLE ROW LEVEL SECURITY;
```

### Step 4: Verify Setup

Run this query to confirm everything works:

```sql
-- Check table exists
SELECT * FROM public.tiktok LIMIT 5;

-- Check indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename = 'tiktok';
```

### Database Schema Overview

The `tiktok` table stores trending hashtag data with these columns:

- **id** - Auto-incrementing primary key
- **platform** - Social media platform (Fixed: "TikTok")
- **topic** - Hashtag name (e.g., "#viral")
- **engagement_score** - Calculated score from 1.0 to 10.0
- **sentiment_polarity** - Sentiment score from -1.0 to 1.0
- **sentiment_label** - "Positive", "Neutral", or "Negative"
- **posts** - Number of posts using this hashtag
- **views** - Total views for this hashtag
- **language** - Detected language code
- **language_confidence** - Confidence score (0-1)
- **metadata** - JSON with additional info (rank, category, source URL, trend_lifecycle)
- **scraped_at** - Timestamp when data was collected
- **collected_at_hour** - Hour timestamp for deduplication
- **version_id** - UUID to group hashtags from same scrape run

---

## 🔧 Proxy Configuration (Optional)

If you're experiencing connection timeouts or IP blocks, configure a proxy:

### Quick Setup

#### Windows PowerShell:
```powershell
# Free proxy (testing only)
$env:PROXY_SERVER="http://proxy-server.com:8080"

# Authenticated proxy (recommended)
$env:PROXY_SERVER="http://proxy-server.com:8080"
$env:PROXY_USERNAME="your_username"
$env:PROXY_PASSWORD="your_password"
```

#### Linux/Mac:
```bash
export PROXY_SERVER="http://proxy-server.com:8080"
export PROXY_USERNAME="your_username"
export PROXY_PASSWORD="your_password"
```

### Premium Proxy Services (Recommended for Production)

- **Bright Data** - https://brightdata.com/
- **Smartproxy** - https://smartproxy.com/
- **Oxylabs** - https://oxylabs.io/
- **ScraperAPI** - https://scraperapi.com/

### Alternative Solutions (No Proxy Required)

1. **Use Mobile Hotspot** - Connect to mobile data and run
2. **Wait and Retry** - TikTok may temporarily block your IP (try again in 1-2 hours)
3. **Use VPN** - Connect to VPN first, then run
4. **GitHub Actions** - Run on cloud infrastructure (already configured if you have GitHub Actions)

### Verifying Proxy Connection

Test if your proxy is working:

```powershell
curl --proxy $env:PROXY_SERVER https://api.ipify.org
```

---

## ⚙️ Configuration

### Engagement Score Calculation

The scraper uses a **log-scaled engagement score** that:
- Converts post counts like `1.2K`, `3.4M`, `2.1B` into integers
- Applies `log10` scaling so very large trends don't dominate
- Adds small bonuses for:
  - High-engagement categories (e.g. Entertainment, Music, Dance, Comedy)
  - Trending keywords in the hashtag (`viral`, `trending`, `challenge`, `fyp`, `foryou`)
  - Short, memorable hashtags

Score range: **1.0–10.0**, clamped after all adjustments.

### Top N Filtering

By default, only the **top 10 hashtags** are uploaded to the database. To change this:

Edit `base.py` around line 835:
```python
# Upload top 20 instead
success = upload_to_supabase(supabase, scraped_data, "tiktok", version_id, top_n=20)
```

### Configuration Constants

Located at the top of `base.py`:

```python
MAX_VIEW_MORE_CLICKS = 25   # Maximum number of "View More" clicks
MIN_WAIT_SEC = 2.0          # Minimum wait between actions
MAX_WAIT_SEC = 5.0          # Maximum wait between actions
MAX_RETRIES = 3             # Number of retry attempts
BASE_BACKOFF_SEC = 2.0      # Base backoff for exponential retry
CHUNK_SIZE = 50             # Chunk size for database inserts
```

---

## 🔧 Troubleshooting

### Connection Timeout Errors

**Problem:** `net::ERR_CONNECTION_TIMED_OUT`

**Solutions:**
1. **Use proxy** - Configure `PROXY_SERVER` environment variable (see Proxy Configuration section)
2. **Wait 1-2 hours** - TikTok may have temporarily blocked your IP
3. **Switch networks** - Use mobile hotspot or different WiFi
4. **Use GitHub Actions** - Run on cloud infrastructure

### No Data in Supabase

**Problem:** Scraper runs successfully but no data visible in Supabase

**Solutions:**
1. Check Row Level Security (RLS) is disabled:
   ```sql
   ALTER TABLE public.tiktok DISABLE ROW LEVEL SECURITY;
   ```

2. Verify data exists:
   ```sql
   SELECT COUNT(*) FROM public.tiktok;
   SELECT * FROM public.tiktok ORDER BY scraped_at DESC LIMIT 10;
   ```

3. Check environment variables are set:
   ```powershell
   echo $env:SUPABASE_URL
   echo $env:SUPABASE_KEY
   ```

### Proxy Not Working

**Problem:** Still getting blocked with proxy configured

**Solutions:**
- Verify proxy is online: `curl --proxy $PROXY_SERVER https://api.ipify.org`
- Try residential proxy instead of datacenter proxy
- Check proxy authentication credentials
- Use GitHub Actions (no proxy needed)

### Chrome Driver Error

**Problem:** `Failed to initialize Chrome driver`

**Solution:**
```bash
# Reinstall Playwright browsers
playwright install chromium
playwright install-deps
```

### Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'playwright'`

**Solution:**
```bash
# Ensure virtual environment is activated
# Then reinstall dependencies
pip install -r requirements.txt
```

### "SUPABASE_URL not set"

**Solution:** Set environment variables (see Step 4 in Quick Start)

### "duplicate key value violates unique constraint"

This is normal! The unique constraint prevents duplicate hashtags in the same hour.

**What happens:**
- First run: Inserts 10 hashtags ✅
- Second run (same hour): Updates existing hashtags ✅
- Next hour: Inserts new batch ✅

---

## 📈 Querying Data

### Latest Scrape
```sql
SELECT topic, engagement_score, posts
FROM public.tiktok
ORDER BY scraped_at DESC
LIMIT 10;
```

### Top Hashtags All-Time
```sql
SELECT 
  topic,
  AVG(engagement_score) as avg_score,
  COUNT(*) as appearances,
  MAX(posts) as max_posts
FROM public.tiktok
GROUP BY topic
ORDER BY avg_score DESC
LIMIT 20;
```

### Trend Over Time
```sql
SELECT 
  DATE_TRUNC('day', scraped_at) as day,
  COUNT(DISTINCT topic) as unique_hashtags,
  AVG(engagement_score) as avg_score
FROM public.tiktok
GROUP BY day
ORDER BY day DESC;
```

### Top Hashtags from Last 24 Hours
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

### Rising Hashtags (Not Seen Before)
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

---

## 🗂️ Project Structure

```
social-media-scraper/
├── base.py                     # TikTok scraper engine
├── scheduler.py                # Scheduler entry point
├── worker_apscheduler.py       # Background worker implementation
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── docs/                       # Comprehensive documentation
├── migrations/                 # Database schema & migrations
└── .env                        # Environment variables (template)
```

---

## 🔒 Security Best Practices

1. **Never commit credentials** - Use environment variables only
2. **Use .gitignore** - Exclude venv, debug files, credentials
3. **Rotate API keys** - Change Supabase keys periodically
4. **Use GitHub Secrets** - For CI/CD credentials
5. **Proxy authentication** - Use authenticated proxies for production

---

## 📦 Dependencies

- `playwright` - Browser automation (Chromium)
- `beautifulsoup4` - HTML parsing
- `supabase` - Database client
- `textblob` & `vaderSentiment` - Sentiment analysis
- `langdetect` - Language detection
- `python-dotenv` - Environment variable loading
- `requests`, `pandas`, `schedule` - Supporting utilities

See `requirements.txt` for exact versions.

---

## 🐛 Debug Mode

Debug HTML files are saved automatically:
- Location: `debug_YYYYMMDD_HHMMSS.html`
- Contains: Full page source for troubleshooting
- Enable: `debug=True` (default)

---

## ⚡ Performance

- **Scraping time:** 4-8 minutes per run
- **Hashtags collected:** 50-200 per run
- **Database upload:** Top 10 only
- **Success rate:** 95%+ with proxy

---

## 🤖 Automated Scheduling

The project can be configured with GitHub Actions for automated runs:

- **Schedule:** Every 3 hours (configurable)
- **Manual trigger:** Via GitHub Actions UI
- **Benefits:** Cloud infrastructure, no local resources, reliable execution

To enable:
1. Add Supabase credentials to GitHub Secrets:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
2. Push to GitHub repository
3. Workflow runs automatically

---

## 💰 Cost & Limits

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

---

## 📝 License

[Add your license here]

---

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Review debug HTML files if available
3. Contact support: [your-email@example.com]

---

## 🎉 Credits

Built with Python, Playwright, and Supabase.

---

**Version:** 1.0.0  
**Last Updated:** November 2025
