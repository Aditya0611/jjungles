# Facebook Trend Scraper 📊

Production-ready Facebook scraper with multiple scraping options, advanced analytics, and database integration.

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Which Scraper to Use?](#-which-scraper-to-use)
- [Usage Examples](#-usage-examples)
- [Supabase Database Setup](#-supabase-database-setup)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browser (for standard/industrial scrapers)
playwright install firefox

# Download TextBlob corpora (for sentiment analysis)
python -m textblob.download_corpora
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Required: Facebook Credentials
FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

# Optional: Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here

# Optional: Proxy List (comma-separated)
PROXIES=http://proxy1:8080,http://proxy2:8080

# Optional: Facebook Cookies (for perfect_scraper)
FACEBOOK_COOKIES_FILE=cookies.txt
```

### 3. Run the Scraper

```bash
# Run automated scraper for all categories
python automated_scraper.py
```

This will automatically:
- Scrape all categories from `config/categories.json`
- Save results to `data/facebook_top10_*.json` files
- Upload to Supabase (if configured)
- Generate logs in `logs/scraper.log`

---

## 📦 Installation

### Requirements

- **Python**: 3.8 or higher
- **Browser**: Firefox (installed via Playwright)
- **RAM**: 2GB minimum
- **Internet**: Stable connection required

### Step-by-Step Installation

1. **Clone or download the project**

2. **Create virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browser**:
   ```bash
   playwright install firefox
   ```

5. **Download TextBlob data**:
```bash
   python -m textblob.download_corpora
   ```

6. **Create `.env` file** with your credentials (see Configuration section)

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Required: Facebook Login
FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

# Optional: Supabase Database
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Optional: Proxy Rotation
PROXIES=http://proxy1:8080,http://proxy2:8080,http://proxy3:8080

# Optional: Cookies File (for perfect_scraper)
FACEBOOK_COOKIES_FILE=cookies.txt

# Optional: Facebook App (for Graph API)
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret

# Optional: Crawlbase API
CRAWLBASE_API_TOKEN=your_token
```

### Configuration Files

#### `config/categories.json`
Defines available categories for scraping:
```json
{
  "technology": "Technology",
  "business": "Business",
  "health": "Health",
  "food": "Food",
  "travel": "Travel",
  "fashion": "Fashion",
  "entertainment": "Entertainment",
  "sports": "Sports"
}
```

#### `config/industrial_config.json`
Industrial scraper settings:
```json
{
  "scraper": {
    "rate_limit_per_minute": 30,
    "max_concurrent": 1
  },
  "proxy": {
    "enabled": true,
    "health_check_interval": 300,
    "max_failures": 3
  },
  "session": {
    "enabled": true,
    "ttl_seconds": 3600
  }
}
```

---

## 🎯 Which Scraper to Use?

### Comparison Table

| Scraper | File | Dependencies | Best For | Cost | Setup |
|---------|------|--------------|----------|------|-------|
| **Standard Scraper** | `base.py` | None (standalone) | Basic scraping, learning | FREE | Easy |
| **Industrial Scraper** | `industrial_scraper.py` | Requires `base.py` | Production, high-volume | FREE | Medium |
| **Perfect Scraper** | `perfect_scraper.py` | None (standalone) | Website display, API | FREE | Easy |
| **Free API Scraper** | `free_api_scraper.py` | None (standalone) | Quick testing | FREE | Easy |

### File Dependencies

**Playwright-Based Scrapers (Chain):**
```
base.py (core logic)
    ↓
industrial_scraper.py (extends base.py)
    ↓
automated_scraper.py (uses industrial_scraper.py)
```

**Standalone Scrapers:**
- `perfect_scraper.py` - No dependencies
- `free_api_scraper.py` - No dependencies

### Recommendations

#### 🏆 **Standard Scraper (base.py)** - Recommended for Most Users
- ✅ **Complete & Standalone** - All logic in one file (3,205 lines)
- ✅ **No Dependencies** - Can be used directly
- ✅ **Full Features** - Login, scraping, analytics, lifecycle tracking
- ✅ **Best for**: Most scraping needs, learning, customization

**Use when**: You need a complete, self-contained scraper

**Files needed:**
- ✅ `base.py` (REQUIRED)
- ✅ `sentiment_analyzer.py` (REQUIRED - used by base.py)

#### 🏭 **Industrial Scraper** - For Production
- ✅ **Extends base.py** - Inherits all features from base.py
- ✅ **Advanced Features** - Rate limiting, enhanced proxy management
- ✅ **Session Persistence** - Avoids repeated logins
- ✅ **Monitoring** - Real-time metrics and statistics
- ✅ **Best for**: High-volume production scraping

**Use when**: You need production-grade features on top of base.py

**Files needed:**
- ✅ `base.py` (REQUIRED - core logic)
- ✅ `industrial_scraper.py` (REQUIRED - extends base.py)
- ✅ `sentiment_analyzer.py` (REQUIRED - used by base.py)
- ✅ `automated_scraper.py` (OPTIONAL - for automation)

#### ⭐ **Perfect Scraper** - Alternative Approach
- ✅ **Standalone** - Doesn't use base.py (different approach)
- ✅ **Library-Based** - Uses facebook-scraper library
- ✅ **No Browser** - Faster, more reliable
- ✅ **Best for**: Website display, API integration

**Use when**: You prefer library-based approach over browser automation

**Files needed:**
- ✅ `perfect_scraper.py` (REQUIRED - standalone)

#### 🆓 **Free API Scraper** - For Quick Testing
- ✅ **Standalone** - No dependencies
- ✅ **No Login** - Uses third-party APIs
- ✅ **Best for**: Quick testing, small projects

**Use when**: You want to test quickly without Facebook login

**Files needed:**
- ✅ `free_api_scraper.py` (REQUIRED - standalone)

---

## 💻 Usage

### Run the Automated Scraper

**Simple command to run everything:**

```bash
python automated_scraper.py
```

**What it does:**
1. ✅ Loads all categories from `config/categories.json`
2. ✅ Logs in to Facebook automatically
3. ✅ Scrapes top 10 hashtags for each category
4. ✅ Saves results to `data/facebook_top10_*.json` files
5. ✅ Uploads to Supabase database (if configured)
6. ✅ Generates logs in `logs/scraper.log`

**Configuration (via environment variables in `.env`):**
```env
# Required
FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

# Optional
MAX_POSTS=100              # Max posts per category (default: 100)
USE_PROXIES=false          # Enable proxy rotation (default: false)
RATE_LIMIT=30              # Requests per minute (default: 30)
HEADLESS=true              # Run browser in headless mode (default: true)
SUPABASE_URL=...           # Supabase URL (optional)
SUPABASE_ANON_KEY=...      # Supabase key (optional)
```

**Output:**
- JSON files: `data/facebook_top10_{category}_{timestamp}.json`
- Supabase: Automatic upload (if configured)
- Logs: `logs/scraper.log`

**Files required:**
- `base.py` (REQUIRED - core logic)
- `industrial_scraper.py` (REQUIRED - extends base.py)
- `automated_scraper.py` (REQUIRED - the script)
- `sentiment_analyzer.py` (REQUIRED - used by base.py)
- `config/categories.json` (REQUIRED - category configuration)

---

## 🗄️ Supabase Database Setup

### Step 1: Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Sign up (free tier available)
3. Create a new project
4. Wait 2-3 minutes for setup

### Step 2: Get Credentials

1. Go to **Project Settings** → **API**
2. Copy **Project URL** (e.g., `https://xxxxx.supabase.co`)
3. Copy **anon public** key (this is your `SUPABASE_ANON_KEY`)

### Step 3: Create Database Table

1. Go to **SQL Editor** in Supabase dashboard
2. Click **New query**
3. Run this SQL:

```sql
-- Create facebook table for storing hashtag trends
CREATE TABLE IF NOT EXISTS public.facebook (
  id BIGSERIAL NOT NULL,
  platform TEXT NOT NULL DEFAULT 'Facebook'::text,
  topic_hashtag TEXT NOT NULL,
  engagement_score DOUBLE PRECISION NULL,
  sentiment_polarity DOUBLE PRECISION NULL,
  sentiment_label TEXT NULL,
  posts BIGINT NULL,
  views BIGINT NULL,
  metadata JSONB NULL,
  scraped_at TIMESTAMPTZ NULL DEFAULT NOW(),
  version_id UUID NOT NULL,
  CONSTRAINT facebook_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_facebook_scraped_at ON public.facebook USING btree (scraped_at);
CREATE INDEX IF NOT EXISTS idx_facebook_version_id ON public.facebook USING btree (version_id);
CREATE INDEX IF NOT EXISTS idx_facebook_hashtag ON public.facebook USING btree (topic_hashtag);
CREATE INDEX IF NOT EXISTS idx_facebook_engagement_score ON public.facebook USING btree (engagement_score DESC);

-- Enable Row Level Security
ALTER TABLE public.facebook ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations
CREATE POLICY IF NOT EXISTS "Allow all operations" ON public.facebook
  FOR ALL
  USING (true)
  WITH CHECK (true);
```

4. Click **Run** to execute

### Step 4: Configure .env

Add to your `.env` file:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

### Step 5: Verify Setup

Run the test script:
```bash
python test_supabase.py
```

### Querying Data

#### Using Supabase Dashboard
1. Go to **Table Editor** → **facebook**
2. View, filter, and search records

#### Using SQL
```sql
-- Get latest hashtags
SELECT * FROM facebook 
ORDER BY scraped_at DESC 
LIMIT 10;

-- Get hashtags by category
SELECT * FROM facebook 
WHERE metadata->>'category' = 'technology'
ORDER BY (metadata->>'trending_score')::float DESC;

-- Get top trending hashtags
SELECT 
  topic_hashtag,
  engagement_score,
  (metadata->>'trending_score')::float as trending_score,
  (metadata->>'category') as category
FROM facebook
ORDER BY (metadata->>'trending_score')::float DESC
LIMIT 20;
```

#### Using Python
```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_ANON_KEY')
)

# Get latest hashtags
result = supabase.table('facebook')\
    .select('*')\
    .order('scraped_at', desc=True)\
    .limit(10)\
    .execute()

for record in result.data:
    print(f"#{record['topic_hashtag']}: {record['engagement_score']}/10")
```

---

## ✨ Features

### Analytics

- **Engagement Score** (1-10): Weighted by likes, comments, shares
- **Trending Score** (0-100): Multi-factor algorithm
  - 22% Engagement (normalized)
  - 18% Post count (logarithmic)
  - 12% Total engagement (logarithmic)
  - 12% Average engagement (logarithmic)
  - 8% Sentiment (polarity)
  - 20% Time decay (exponential, 12-hour half-life)
  - 4% Consistency (coefficient of variation)
  - 4% Velocity (growth rate)
- **Sentiment Analysis**: Positive/Neutral/Negative with TextBlob
- **Language Detection**: Automatic language detection with confidence scores
- **Time Weighting**: Exponential decay favoring recent trends

### Lifecycle Tracking

- **version_id**: Unique identifier for each scraping run
- **first_seen**: Timestamp when trend was first detected
- **last_seen**: Timestamp when trend was last seen
- **scraped_at**: Current scraping timestamp

### Output Formats

- **JSON files**: `data/facebook_top10_{category}_{timestamp}.json`
- **Supabase**: Automatic upload to database (optional)
- **Logs**: Structured JSON in `logs/scraper.log`

### Categories

Technology | Business | Health | Food | Travel | Fashion | Entertainment | Sports

---

## 📁 Project Structure

### Core Files & Dependencies

```
base.py (3,205 lines) ⭐ CORE FILE
├── Contains ALL core logic:
│   ├── BaseScraper class (browser, logging, utilities)
│   ├── FacebookScraper class (login, scraping, analytics)
│   ├── All methods: login(), get_top_10_trending(), save_results()
│   ├── Analytics, sentiment analysis, lifecycle tracking
│   └── Complete, self-contained scraper
│
└── Used by:
    ├── industrial_scraper.py (extends FacebookScraper)
    └── automated_scraper.py (uses industrial_scraper → uses base.py)

industrial_scraper.py
├── Extends: FacebookScraper from base.py
├── Adds: Rate limiting, enhanced proxy management, metrics
└── Requires: base.py (must be present)

automated_scraper.py
├── Uses: industrial_scraper.py
└── Requires: industrial_scraper.py + base.py (chain dependency)

perfect_scraper.py
└── Standalone - Different approach (library-based, doesn't use base.py)
```

### Complete File Structure

```
facebook_scraper/
├── base.py                       # ⭐ CORE - All logic (3,205 lines)
├── industrial_scraper.py         # Extends base.py (requires base.py)
├── automated_scraper.py          # Uses industrial_scraper (requires both)
├── perfect_scraper.py            # Standalone (alternative approach)
├── free_api_scraper.py           # Standalone (alternative approach)
├── sentiment_analyzer.py          # Utility (used by base.py)
├── demo.py                        # Standard scraper demo
├── industrial_demo.py             # Industrial scraper demo
├── perfect_demo.py                # Perfect scraper demo
├── free_api_demo.py               # Free API demo
├── test_supabase.py               # Supabase connection test
├── requirements.txt               # Python dependencies
├── create_supabase_table.sql      # Database schema
├── config/
│   ├── categories.json            # Category configuration
│   └── industrial_config.json     # Industrial scraper settings
├── sessions/                      # Session storage (auto-created)
├── data/                          # Scraped data output
└── logs/                          # JSON logs
```

### Dependency Chain

**Playwright-Based Scrapers:**
```
base.py (core logic)
    ↓
industrial_scraper.py (extends base.py)
    ↓
automated_scraper.py (uses industrial_scraper.py)
```

**All three files required for automated_scraper.py to work!**

**Standalone Scrapers:**
- `perfect_scraper.py` - No dependencies
- `free_api_scraper.py` - No dependencies

---

## 🛠️ Troubleshooting

### Login Issues

**Problem**: Login fails or gets stuck

**Solutions**:
- ✅ Disable 2FA temporarily
- ✅ Run with `headless=False, debug=True` to see browser
- ✅ Check credentials in `.env` file
- ✅ Clear browser cache/cookies
- ✅ Try different browser (Firefox/Chromium)

### No Results Found

**Problem**: Scraper runs but finds 0 posts

**Solutions**:
- ✅ Verify category exists in `config/categories.json`
- ✅ Increase `max_posts` parameter
- ✅ Check `logs/scraper.log` for errors
- ✅ Try different category
- ✅ Use Perfect Scraper instead (more reliable)

### Browser Not Found

**Problem**: `playwright: command not found` or browser errors

**Solutions**:
```bash
# Install Playwright browsers
playwright install firefox
playwright install chromium  # Optional
```

### Dependencies Errors

**Problem**: Import errors or missing packages

**Solutions**:
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Install TextBlob corpora
python -m textblob.download_corpora

# Verify installation
python -c "import playwright; import supabase; import textblob"
```

### Supabase Connection Issues

**Problem**: "Supabase credentials not found" or connection errors

**Solutions**:
- ✅ Check `.env` file exists and has correct values
- ✅ Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
- ✅ Restart script after editing `.env`
- ✅ Test connection with `python test_supabase.py`
- ✅ Check Supabase project is active (not paused)

### Proxy Issues

**Problem**: Proxy rotation not working

**Solutions**:
- ✅ Verify proxy format in `.env`: `PROXIES=http://proxy1:8080,http://proxy2:8080`
- ✅ Test proxies manually
- ✅ Check proxy credentials if required
- ✅ Increase `max_failures` in config if proxies are flaky

### Rate Limiting

**Problem**: Getting blocked or rate limited

**Solutions**:
- ✅ Reduce `rate_limit_per_minute` in config
- ✅ Increase delays between requests
- ✅ Use proxy rotation
- ✅ Use session persistence
- ✅ Rotate proxies more frequently

---

## 🔒 Security

### Best Practices

- ✅ **Never commit `.env` file** - Add to `.gitignore`
- ✅ **Use environment variables** - Never hardcode credentials
- ✅ **Keep dependencies updated** - Run `pip install -r requirements.txt --upgrade` regularly
- ✅ **Review logs regularly** - Check for suspicious activity
- ✅ **Use secure passwords** - Strong Facebook password
- ✅ **Enable 2FA on Facebook** - Better account security

### Environment Variables

Never share or commit:
- `FACEBOOK_EMAIL`
- `FACEBOOK_PASSWORD`
- `SUPABASE_ANON_KEY` (if using service role key)
- `FACEBOOK_APP_SECRET`
- `CRAWLBASE_API_TOKEN`

Safe to share:
- `SUPABASE_URL` (public)
- `SUPABASE_ANON_KEY` (anon/public key is safe)

### Session Files

- Session files in `sessions/` contain cookies
- Keep them secure and don't share
- They're automatically created and managed

---

## 📊 Data Model

### TrendRecord Schema

```python
@dataclass
class TrendRecord:
    platform: str
    topic_hashtag: str
    engagement_score: float          # 1-10
    trending_score: float            # 0-100
    sentiment_polarity: float        # -1 to +1
    sentiment_label: str             # "positive", "negative", "neutral"
    post_count: int
    total_engagement: int
    avg_engagement: float
    likes: int
    comments: int
    shares: int
    views: int
    category: str
    version_id: str                   # UUID for scraping run
    first_seen: datetime             # First detection timestamp
    last_seen: datetime              # Last seen timestamp
    scraped_at: datetime             # Current scraping timestamp
    is_estimated: bool
    confidence_score: float          # 0-1
```

### Output JSON Example

```json
  {
    "platform": "Facebook",
    "topic_hashtag": "AI",
    "engagement_score": 8.5,
    "trending_score": 92.3,
    "sentiment_polarity": 0.65,
    "sentiment_label": "positive",
    "post_count": 45,
    "total_engagement": 125000,
    "avg_engagement": 2777.8,
    "likes": 85000,
    "comments": 30000,
    "shares": 10000,
    "category": "technology",
    "version_id": "abc-123-def-456",
  "first_seen": "2025-01-15T10:00:00",
  "last_seen": "2025-01-15T14:30:00",
  "scraped_at": "2025-01-15T14:30:00"
}
```

---

## 🚀 Advanced Features

### Proxy Rotation

Configure in `.env`:
```env
PROXIES=http://proxy1:8080,http://proxy2:8080,http://proxy3:8080
```

Rotation settings (in `base.py`):
- `max_requests_per_proxy`: 50 requests
- `max_time_per_proxy`: 1800 seconds (30 minutes)
- `rotate_on_failure`: True
- `rotate_between_hashtags`: True

### Session Persistence

Sessions are automatically saved in `sessions/` directory:
- Avoids repeated logins
- Cookie management
- Session TTL and expiration
- Automatic recovery

### Rate Limiting

Industrial scraper uses token bucket algorithm:
- Configurable requests per minute
- Automatic backoff on rate limits
- Burst support
- Smart throttling

### Metrics & Monitoring

Get real-time statistics:
```python
metrics = scraper.get_metrics()
# Returns:
# - total_requests, successful_requests, failed_requests
# - success_rate, avg_response_time
# - proxy_stats (health, success rates)
# - uptime, posts_scraped, hashtags_found
```

---

## 📝 Requirements

- **Python**: 3.8 or higher
- **Browser**: Firefox (installed via Playwright)
- **RAM**: 2GB minimum (4GB recommended)
- **Internet**: Stable connection required
- **Storage**: ~500MB for dependencies and data

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## 🆘 Support

For issues or questions:
1. Check `logs/scraper.log` for error details
2. Review Troubleshooting section above
3. Verify configuration in `.env` file
4. Test with demo scripts first

---

**Ready to scrape! 🎉**

For the best experience, start with **Perfect Scraper** (`python perfect_demo.py`) - it's the most reliable and requires no browser setup.
