# LinkedIn Trending Hashtags Scraper

> [!NOTE]
> **Sprint 1 Delivery Status**: READY
> This project is currently optimized for **LinkedIn** scraping. While the architecture supports multiple platforms, other social media scrapers (FB, IG, etc.) are currently in stub/placeholder state for future sprints.

A professional tool for scraping and analyzing trending hashtags from LinkedIn feeds. This scraper extracts hashtags, performs sentiment analysis, calculates engagement scores, and stores data in Supabase.

## ✨ Features

- **Automated Scraping**: Scrolls through LinkedIn feed automatically
- **Hashtag Extraction**: Identifies and counts trending hashtags
- **Sentiment Analysis**: Uses 3 methods (TextBlob, VADER, Transformer) for accurate sentiment detection
- **Engagement Scoring**: Calculates engagement scores based on frequency, diversity, and sentiment
- **Language Detection**: Automatically detects language of hashtag contexts
- **Supabase Integration**: Automatic database storage with full metadata
- **Anti-Detection**: Stealth features and human-like behavior to avoid detection
- **Proxy Support**: Optional proxy rotation for enhanced reliability
- **Progress Tracking**: Real-time progress indicators and performance metrics

## 📋 Prerequisites

- **Python 3.8 or higher**
- **LinkedIn Account** (for login)
- **Supabase Account** (for database storage - optional but recommended)
- **Windows/Mac/Linux** (cross-platform support)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or extract the project
cd linkedin-hashtag-scraper

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python setup_playwright.py
```

### 2. Configuration

#### Supabase Setup (Required for Database Storage)

1. **Create a Supabase project** at https://supabase.com

2. **Run the database schema:**
   - Open Supabase Dashboard → SQL Editor
   - Copy and paste the contents of your `linkedin` table schema.
   - Also run the `scrape_logs` table schema (found in the walkthrough or `unified_trends_schema.sql`).
   - Note: This creates the tables required for LinkedIn hashtag analysis and run logging.

3. **Get your Supabase credentials:**
   - Go to Settings → API
   - Copy your `Project URL` and `anon public` key

4. **Configure environment variables:**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your credentials:
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   USE_SUPABASE=true
   ```

#### Proxy Setup (Optional)

1. Create or edit `proxies.txt`
2. Add proxies, one per line:
   ```
   host:port
   host:port:username:password
   ```
3. Set `USE_PROXIES=true` in `.env` file

### 3. Run the Scraper

```bash
python linkedin_hashtag_scraper_playwright.py
```

**First Run:**
1. Browser will open automatically
2. **Manually log in to LinkedIn** (recommended for security)
3. The scraper will automatically start collecting hashtags
4. Results will be saved to `trending_hashtags.json` and Supabase
5. Logs are available in `scraper.log` for detailed debugging

### 4. Validation Steps (Proof of Life)

After installation, verify the scraper is working correctly with these validation steps:

#### Step 1: Run Smoke Tests

```bash
python tests/test_linkedin_scraper_smoke.py
```

**Expected Outcome:**
```
Ran 5 tests in X.XXXs

OK
```

All tests should pass. If any test fails, check the error message and verify your setup.

#### Step 2: Run a Short Scrape

Edit `.env` file and set:
```env
MAX_SCROLLS=2
```

Then run the scraper:
```bash
python linkedin_hashtag_scraper_playwright.py
```

**Expected Outcome:**
- Console displays real-time progress: "Scroll 1/2", "Scroll 2/2"
- Console shows "Top 10 Trending Hashtags" table with hashtags, sentiment, and engagement scores
- Console shows "Run Completed (status: success)"
- File `trending_hashtags.json` is created with results

#### Step 3: Verify Supabase Data

Run this SQL query in Supabase SQL Editor:

```sql
-- Check recent data
SELECT 
    platform,
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    scraped_at
FROM public.linkedin
WHERE scraped_at > NOW() - INTERVAL '5 minutes'
ORDER BY scraped_at DESC
LIMIT 10;

-- Check row count
SELECT COUNT(*) as total_linkedin_records
FROM public.linkedin;
```

**Expected Outcome:**
- At least 1-10 new rows with today's timestamp
- Each row has `platform = 'linkedin'`, a hashtag, engagement score, and sentiment label
- Row count increases after each scrape

**Troubleshooting Validation:**
- **No hashtags found**: LinkedIn feed may be empty or login required. Ensure you're logged in.
- **No Supabase data**: Check `.env` has correct `SUPABASE_URL` and `SUPABASE_ANON_KEY`. Verify `unified_trends_schema.sql` was run to create the `trends` table.
- **Tests fail**: Check Python version (3.8+), reinstall dependencies: `pip install -r requirements.txt`

## 📊 Output

### Console Output
The scraper displays:
- Real-time progress (scrolls, hashtags collected, speed)
- Top 10 trending hashtags with sentiment analysis
- Engagement scores with breakdown
- Collection statistics

### JSON File
Results are saved to `trending_hashtags.json` with:
- Total hashtags collected
- Unique hashtags
- Top 10 trending hashtags
- Sentiment analysis results
- Language detection

### Supabase Database
Data is automatically saved to the `linkedin` table with:
- Hashtag name
- Engagement score
- Sentiment analysis (all 3 methods)
- Post count
- Metadata (caption, language, detailed sentiment)
- Timestamp

## ⚙️ Configuration Options

You can customize the scraper by editing the `.env` file:

```env
# Scraper Settings
SCROLL_PAUSE_TIME=1.5      # Time between scrolls (seconds)
MAX_SCROLLS=50             # Maximum number of scrolls
OUTPUT_FILE=trending_hashtags.json

# Browser Settings
HEADLESS=false             # Run browser in background (true/false)
BROWSER_LOCALE=en-US       # Browser locale
BROWSER_TIMEZONE=America/New_York

# Proxy Settings
USE_PROXIES=false          # Enable proxy rotation
ROTATE_PROXY_EVERY=10      # Rotate proxy after N scrolls
```

## 📈 Understanding Engagement Scores

Engagement scores (0-100) are calculated using three factors:

1. **Frequency Score (0-50 points)**: How often the hashtag appears
2. **Post Diversity Score (0-30 points)**: How many unique posts contain it
3. **Sentiment Boost (0-20 points)**: Positive sentiment increases score

**Example:**
- Hashtag appears 3 times → Frequency: 2.4 points
- In 2 unique posts → Diversity: 1.7 points
- Positive sentiment → Sentiment: 16.8 points
- **Total Engagement Score: 20.9/100**

## 🔍 Viewing Data in Supabase

### Using SQL Editor

```sql
-- View latest LinkedIn records
SELECT 
    platform,
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    scraped_at
FROM public.linkedin
ORDER BY scraped_at DESC
LIMIT 20;

-- View top hashtags by engagement
SELECT 
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts
FROM public.linkedin
ORDER BY engagement_score DESC
LIMIT 10;

-- View metadata (caption, language, detailed sentiment)
SELECT 
    topic_hashtag,
    engagement_score,
    metadata->>'caption' as caption,
    metadata->>'language' as language
FROM public.linkedin
ORDER BY scraped_at DESC
LIMIT 10;
```

### Using Table Editor
1. Go to Supabase Dashboard
2. Click "Table Editor"
3. Select the `linkedin` table

## 🛡️ Anti-Detection Features

- **Stealth Mode**: Removes automation indicators
- **Random User Agents**: Rotates user agents
- **Human-like Scrolling**: Natural scroll patterns with random delays
- **Proxy Rotation**: Changes IP address periodically (if configured)
- **Random Delays**: Mimics human behavior

## ⚠️ Important Notes

### Legal and Ethical Considerations
- **LinkedIn's Terms of Service** prohibit automated scraping
- Use this tool responsibly and at your own risk
- Respect rate limits and don't overload LinkedIn's servers
- Consider using LinkedIn's official API for legitimate use cases
- This tool is for **educational and research purposes**

### Best Practices
- Use manual login (more secure)
- Don't scrape too aggressively (use reasonable scroll limits)
- Use proxies if scraping frequently
- Monitor for rate limiting or blocks
- Respect LinkedIn's infrastructure

## 🔧 Troubleshooting

### No Data in Supabase
1. Check `.env` file has correct `SUPABASE_URL` and `SUPABASE_ANON_KEY`
2. Verify table exists: Run `linkedin_table_schema.sql` in Supabase
3. Check Supabase logs for errors
4. Run: `SELECT COUNT(*) FROM public.linkedin;` to verify data

### Browser Not Opening
- Install Playwright: `python setup_playwright.py`
- Or manually: `playwright install chromium`

### Login Issues
- Use manual login (browser will open)
- Clear browser cache if needed
- Check if LinkedIn requires 2FA

### Slow Performance
- Reduce `MAX_SCROLLS` in `.env`
- Increase `SCROLL_PAUSE_TIME`
- Use faster proxies

### Getting Blocked
- Use proxies (`USE_PROXIES=true`)
- Reduce scroll speed
- Increase delays between actions
- Rotate proxies more frequently

## 📁 Project Structure

```
linkedin-hashtag-scraper/
├── linkedin_hashtag_scraper_playwright.py  # [REQUIRED] Main scraper script
├── requirements.txt                         # [REQUIRED] Python dependencies
├── setup_playwright.py                     # [REQUIRED] Browser setup script
├── .env.example                            # [REQUIRED] Environment template
├── proxies.txt                             # [OPTIONAL] Proxy configuration
├── logger.py                               # [REQUIRED] Logging utility
├── base_scraper.py                         # [REQUIRED] Base class for scrapers
├── README.md                               # This file
├── config.py                               # Configuration settings
│
├── utils/                                  # [REQUIRED] Modular utilities
│   ├── analysis.py                         # Sentiment & Language logic
│   └── proxies.py                          # Proxy rotation logic
│
├── linkedin_table_schema.sql               # [SETUP] Run once to create Supabase tables
├── view_linkedin_data.sql                  # [HELPER] Useful SQL queries for analysis
├── qa_dashboard.html                       # [HELPER] Simple HTML dashboard to view results
└── tests/                                  # [TEST] Validation tests
    └── test_linkedin_scraper_smoke.py
```

## 📝 License

This project is for **educational and research purposes only**. Use responsibly and in accordance with LinkedIn's Terms of Service.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Supabase logs for database errors
3. Check console output for error messages
4. Verify all environment variables are set correctly

## 📊 Example Output

```
🔥 TOP 10 TRENDING HASHTAGS ON LINKEDIN
======================================================================
 1. #artificialintelligence        📊   4 times (  3.4%)
     💬 Sentiment: 😊 POSITIVE
     🌐 Language: EN (confidence: 100.0%)
     📊 Engagement Score: 17.8/100

 2. #innovation                    📊   4 times (  3.4%)
     💬 Sentiment: 😊 POSITIVE
     🌐 Language: EN (confidence: 100.0%)
     📊 Engagement Score: 17.9/100
...
```

---

**Version:** 1.0  
**Last Updated:** 2024  
**Maintained by:** [Your Name/Company]
