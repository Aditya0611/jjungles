# YouTube Trending Hashtags Scraper - Sprint-1 Edition

A robust, production-ready scraper to extract and aggregate trending YouTube hashtags with **strict proxy enforcement**, **Supabase integration**, and **Odoo scheduler support**.

## 🚀 Sprint-1 Features

### Core Capabilities
- ✅ **Strict Proxy Enforcement** - No bypass allowed, explicit failures when proxies are blocked
- ✅ **Proxy Rotation** - Round-robin rotation through configurable proxy list
- ✅ **YouTube Data API v3** - High-speed trending video collection
- ✅ **Supabase Integration** - Automatic data storage with retry logic
- ✅ **Odoo Scheduler** - Admin-configurable scraping frequency
- ✅ **Sentiment Analysis** - TextBlob-powered sentiment scoring
- ✅ **Engagement Scoring** - Calculated from views, likes, and comments
- ✅ **Comprehensive Logging** - All operations logged with appropriate levels

### Technical Features
- Headless Playwright with stealth-like behavior
- Concurrency control with retries and exponential backoff
- Multi-locale and category scraping
- Streamlit dashboard for analytics
- Comprehensive test suite

---

## 📋 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
python -m playwright install
```

### 2. Configure Environment Variables

```bash
copy .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required
YOUTUBE_API_KEY=your_youtube_api_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Proxy Configuration (Sprint-1 Requirement)
PROXY_LIST=http://proxy1:port,http://proxy2:port,http://proxy3:port
PROXY_STRICT_MODE=true  # Enforces proxy usage, no bypass allowed

# Database
USE_DATABASE=true

# Optional
HEADLESS=false
CONCURRENCY=6
```

### 3. Setup Supabase Database

Run this SQL in your Supabase SQL Editor:

```sql
-- Create youtube table (if not exists)
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_youtube_platform ON public.youtube(platform);
CREATE INDEX IF NOT EXISTS idx_youtube_hashtag ON public.youtube(topic_hashtag);
CREATE INDEX IF NOT EXISTS idx_youtube_scraped_at ON public.youtube(scraped_at);

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

## 🔧 Configuration Options

### CLI Arguments

```bash
python main.py \
  --locales US,IN,GB \
  --categories music,gaming \
  --limit 200 \
  --concurrency 6 \
  --top 10 \
  --headless true \
  --output out
```

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `YOUTUBE_API_KEY` | YouTube Data API key | - | ✅ Yes |
| `SUPABASE_URL` | Supabase project URL | - | ✅ Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | - | ✅ Yes |
| `PROXY_LIST` | Comma-separated proxy list | - | ✅ Yes (Sprint-1) |
| `PROXY_STRICT_MODE` | Enforce proxy usage | `true` | No |
| `USE_DATABASE` | Enable Supabase storage | `false` | No |
| `HEADLESS` | Run browser in headless mode | `false` | No |
| `CONCURRENCY` | Parallel video processing | `6` | No |

---

## 🧪 Testing

### Proxy Enforcement Tests

```bash
python tests\test_proxy_enforcement.py
```

Expected output:
```
✅ PASSED: Strict Mode - No Proxies
✅ PASSED: Strict Mode - With Proxies
✅ PASSED: Non-Strict Mode - No Proxies
✅ PASSED: Proxy List Validation
Total: 4/4 tests passed
```

### Database Integration Tests

```bash
python tests\test_db_integration.py
```

### Configuration Check

```bash
python tests\check_config.py
```

---

## 📊 Streamlit Dashboard

Launch the analytics dashboard:

```bash
streamlit run streamlit_app.py
```

Features:
- Real-time trending hashtags
- Engagement score visualization
- Sentiment distribution
- Platform filtering
- Scraping logs monitoring

---

## 🔄 Odoo Integration

### Installation

1. Copy the Odoo addon:
   ```bash
   cp -r odoo_addons/youtube_scraper_scheduler /path/to/odoo/addons/
   ```

2. Update Odoo apps list: **Settings → Apps → Update Apps List**

3. Install addon: Search for "YouTube Scraper Scheduler" and click Install

### Configuration

Navigate to: **Settings → YouTube Scraper → Settings**

Configure:
- **Scrape Frequency**: Every [N] [minutes/hours/days/weeks/months]
- **Scraper Path**: Absolute path to project directory
- **Python Executable**: Path to Python or virtual environment

The cron job will automatically run the scraper on the configured schedule.

---

## 🛡️ Sprint-1 Proxy Enforcement

### How It Works

1. **Strict Mode Enabled** (`PROXY_STRICT_MODE=true`):
   - Scraper **will not run** without proxies
   - Explicit error message if proxy list is empty
   - Fails immediately on startup

2. **Proxy Rotation**:
   - Round-robin through provided proxy list
   - All proxies logged on startup
   - Each request rotates to next proxy

3. **Error Handling**:
   - Clear error messages for proxy failures
   - Retry logic with exponential backoff
   - All proxy operations logged

### Example Error (No Proxies):

```
ERROR: PROXY ENFORCEMENT FAILURE: No proxies available in strict mode.
Scraper cannot run without proxies. Please configure PROXY_LIST in .env file.
Exit code: 1
```

---

## 📁 Project Structure

```
utube scrapping/
├── src/
│   ├── config.py           # Configuration management
│   ├── proxy.py            # Proxy rotation with strict mode
│   ├── scraper.py          # YouTube scraping logic
│   ├── pipeline.py         # Main orchestration
│   ├── supabase_storage.py # Database integration
│   ├── sentiment.py        # Sentiment analysis
│   └── logger.py           # Logging setup
├── tests/
│   ├── test_proxy_enforcement.py
│   ├── test_db_integration.py
│   └── check_config.py
├── odoo_addons/
│   └── youtube_scraper_scheduler/  # Odoo addon
├── main.py                 # Entry point
├── streamlit_app.py        # Dashboard
└── .env.example            # Configuration template
```

---

## 🚨 Troubleshooting

### "PROXY ENFORCEMENT FAILURE"
- **Solution**: Add `PROXY_LIST` to `.env` or set `PROXY_STRICT_MODE=false`

### "Database connection failed"
- **Solution**: Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`
- **Solution**: Ensure `youtube` table exists (run SQL setup)

### "Table 'youtube' does not exist"
- **Solution**: Run the SQL setup script in Supabase SQL Editor

### Odoo cron not running
- **Solution**: Check scraper path and Python executable in Odoo settings
- **Solution**: Verify Odoo user has read/execute permissions

---

## 📝 Notes and Best Practices

- **Respect rate limits**: YouTube API has quotas
- **Use proxies**: Required for Sprint-1, recommended for scale
- **Monitor logs**: Check `scraping_logs` table in Supabase
- **Schedule wisely**: Use Odoo scheduler or cron for periodic runs
- **Test first**: Run with `--limit 5` to verify setup

---

## 📄 License

For personal/educational use. Ensure compliance with YouTube Terms of Service and local laws before scraping at scale.

---

## 🎯 Sprint-1 Deliverables

- ✅ Enforced proxy usage with rotation
- ✅ Explicit failure when proxy access is blocked
- ✅ Successful DB insertion for YouTube platform
- ✅ Admin-configurable scrape frequency via Odoo
- ✅ Comprehensive test suite
- ✅ Production-ready documentation

**Status**: Ready for production deployment
