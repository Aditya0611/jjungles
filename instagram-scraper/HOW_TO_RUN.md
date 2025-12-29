# How to Run the Instagram Scraper

## Prerequisites

1. **Install Python 3.10+**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   playwright install-deps chromium
   ```

4. **Download TextBlob corpora (first time only):**
   ```bash
   python -m textblob.download_corpora
   ```

5. **Install VADER (optional, for better sentiment analysis):**
   ```bash
   pip install vaderSentiment
   ```

## Configuration

### 1. Set up Environment Variables
Create a `.env` file in the root directory.

### 2. Using Proxies (Highly Recommended)
By default, the scraper enforces proxy usage for safety.
- Set `REQUIRE_PROXIES=true` in `.env`.
- Configure `PROXY_SERVER`, `PROXY_USERNAME`, and `PROXY_PASSWORD`.

### 3. Running WITHOUT Proxies
If you want to run the scraper using your local IP (not recommended for long-term use):
- Set `REQUIRE_PROXIES=false` in `.env`.
- The scraper will bypass proxy enforcement and use the direct connection.

## Running the Scraper

### Method 1: Run Once (Test Mode)

Run the scraper once for testing:

```bash
python main.py --run-once
```

This will:
- Discover trending hashtags from Instagram Explore page
- Analyze engagement for top hashtags
- Perform sentiment analysis on posts
- Save data to Supabase
- Exit after completion

### Method 2: Scheduled Mode (Continuous)

Run the scraper with automatic scheduling:

```bash
python main.py
```

This will:
- Run the scraper every 3 hours (configurable)
- Continue running until you stop it (Ctrl+C)
- Automatically discover and analyze trending hashtags

## Running via GitHub Actions (Automated)

The scraper is configured to run automatically on GitHub Actions:

1. **Automatic Schedule:**
   - Runs every 4 hours automatically
   - No action needed - it runs in the background

2. **Manual Trigger:**
   - Go to: https://github.com/Aditya0611/instagram/actions
   - Click "Instagram Trend Analyzer"
   - Click "Run workflow" → "Run workflow"
   - Select branch: `main`
   - Click "Run workflow"

## What the Scraper Does

1. **Logs into Instagram** using your credentials
2. **Discovers trending hashtags** from the Explore page
3. **Categorizes hashtags** (fashion, travel, food, fitness, etc.)
4. **Analyzes engagement** (likes, comments, views) for each hashtag
5. **Performs sentiment analysis** on post captions (Positive 😊, Neutral 😐, Negative 😢)
6. **Saves to Supabase** database with all metrics

## Output

The scraper will display:

```
======================================================================
🔥 INSTAGRAM TRENDING HASHTAG DISCOVERY
   WITH CATEGORIES & REAL ENGAGEMENT
======================================================================

✅ Connected to Supabase
✅ Login successful!

🔍 DISCOVERING TRENDING HASHTAGS
[+] Navigating to Explore page...
[+] Scrolling 15 times to load more posts...
[+] Collecting hashtags from posts...

✅ DISCOVERED 10 TRENDING HASHTAGS

📁 FASHION (2 hashtags)
   #fashion - 15x
   #style - 12x

💾 ANALYZING ENGAGEMENT & SAVING TO DATABASE
[1/10] 📊 FASHION: #fashion
    💯 Average Engagement: 2,845
    👍 Average Likes: 2,607
    💬 Average Comments: 238
    🎭 Sentiment Analysis:
       Overall: POSITIVE 😊
       Distribution: 😊7 😐2 😢1
       Average Score: 0.234
    ✅ Saved successfully
```

## Troubleshooting

### Issue: "Login failed"
- Check your Instagram credentials
- Instagram may require 2FA or show a challenge page
- Try logging in manually first to verify account status

### Issue: "Supabase connection failed"
- Verify your SUPABASE_URL and SUPABASE_KEY
- Check if the `instagram` table exists in Supabase
- Test connection: `python test_supabase_connection.py`

### Issue: "No hashtags found"
- Instagram may have changed their page structure
- Try increasing `POSTS_TO_SCAN` in Config
- Check if you're logged in successfully

### Issue: "Playwright browser error"
- Make sure Playwright browsers are installed: `playwright install chromium`
- On Linux, install dependencies: `playwright install-deps chromium`

## Configuration Options

You can customize these in `main.py` Config class:

- `SCROLL_COUNT`: How many times to scroll (default: 15)
- `POSTS_TO_SCAN`: How many posts to scan (default: 400)
- `TOP_HASHTAGS_TO_SAVE`: How many top hashtags to save (default: 10)
- `POSTS_PER_HASHTAG`: How many posts to analyze per hashtag (default: 3)
- `SCHEDULE_HOURS`: How often to run in scheduled mode (default: 3 hours)

## Checking Results

After running, check your data:

```bash
python check_latest_data.py
```

This will show:
- Latest scraped hashtags
- When they were scraped
- Engagement scores
- Sentiment analysis results

## Stopping the Scraper

If running in scheduled mode:
- Press `Ctrl+C` to stop gracefully
- The scraper will finish the current job before stopping

