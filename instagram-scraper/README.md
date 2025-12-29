# Instagram Trending Hashtag Discovery & Analysis

A comprehensive Instagram scraper that automatically discovers trending hashtags from Instagram's Explore page, extracts real engagement metrics, performs sentiment analysis, and stores structured data in Supabase with lifecycle management.

## 🚀 Key Features

### 🔍 Trending Discovery
- **Automatic Discovery**: Scrapes Instagram's Explore page to discover trending hashtags in real-time
- **Smart Categorization**: Automatically categorizes hashtags into 10+ categories (fashion, fitness, food, travel, technology, business, entertainment, lifestyle, photography, sports)
- **Frequency Analysis**: Tracks hashtag frequency across discovered posts
- **Top Hashtag Selection**: Selects top trending hashtags based on frequency and engagement

### 📊 Engagement Metrics
- **Real Metrics Extraction**: Extracts actual likes, comments, and views from posts
- **Engagement Score Calculation**: Calculates comprehensive engagement scores
- **Content Type Detection**: Identifies content types (photo, reel, video, carousel, carousel_video)
- **Content Distribution**: Tracks distribution of content types per hashtag

### 🎭 Advanced Analysis
- **Sentiment Analysis**: TextBlob and VADER-powered sentiment analysis with polarity scores
- **Language Detection**: Automatic language detection from post captions using `langdetect` (supports 55+ languages)
- **Language Distribution**: Tracks language distribution across posts with confidence scores
- **Localized Filtering**: Filter trends by specific languages for multi-language client accounts
- **Multi-language Support**: Handles Unicode and emoji characters

### 💾 Data Management
- **Supabase Integration**: Stores normalized TrendRecord objects in Supabase
- **Bulk Insert**: Efficient bulk insert with retry mechanisms for new trends
- **Update Existing**: Automatically updates existing trends with new data
- **Version Management**: Tracks scraper runs with unique version IDs
- **Lifecycle Management**: 
  - Archives expired trends (>30 days old)
  - Applies engagement score decay for inactive trends (>14 days)
- **Structured Exports**: Exports data in JSON and CSV formats for easy integration

### 🔄 Automation
- **Scheduled Runs**: Configurable scheduled runs using APScheduler (default: every 3 hours)
- **Manual Login Fallback**: Falls back to manual login if automated login fails
- **Robust Error Handling**: Comprehensive error handling and retry logic
- **Proxy Support**: Optional proxy configuration for enhanced privacy

### 🛡️ Anti-Detection
- **Human-like Behavior**: Randomized delays and typing patterns
- **Playwright Automation**: Uses Playwright for reliable browser automation
- **Cookie Consent Handling**: Automatically handles cookie consent banners
- **Popup Dismissal**: Automatically dismisses Instagram popups and notifications

## 📁 Project Structure

```
instagram/
├── main.py                      # Main scraper script
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI/CD workflow
│       └── instagram_scraper.yml  # Scheduled scraper workflow
└── [generated files]
    ├── trends_export_*.json    # JSON export files
    ├── trends_export_*.csv     # CSV export files
    └── instagram_scraper.log   # Log file
```

## 🛠️ Installation

### Prerequisites
- Python 3.10 or higher
- Chrome/Chromium browser (for Playwright)
- Supabase account and database

### 1. Clone or Download the Project
```bash
git clone <repository-url>
cd instagram
```

### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv vrnv
vrnv\Scripts\activate

# Linux/Mac
python3 -m venv vrnv
source vrnv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```bash
playwright install chromium
```

### 5. Install TextBlob Corpora (First Time)
```python
python -c "from textblob import TextBlob; TextBlob('test').sentiment"
```

## ⚙️ Configuration

### Environment Variables (Recommended)

Create a `.env` file or set environment variables:

```bash
# Instagram Credentials
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional: Proxy Configuration
PROXY_URL=http://proxy.example.com:8080
PROXY_USERNAME=proxy_username
PROXY_PASSWORD=proxy_password

# Optional: Scraper Settings
SCROLL_COUNT=15              # Number of scrolls on Explore page
POSTS_TO_SCAN=400            # Maximum posts to scan
MIN_HASHTAG_FREQUENCY=1      # Minimum frequency to consider hashtag
TOP_HASHTAGS_TO_SAVE=10      # Number of top hashtags to save
POSTS_PER_HASHTAG=3          # Posts to analyze per hashtag
SCHEDULE_HOURS=3             # Hours between scheduled runs

# Optional: Language Detection & Filtering
ENABLE_LANGUAGE_DETECTION=true  # Enable language detection (default: true)
FILTER_LANGUAGES=""            # Filter by languages (comma-separated: "en,es,fr" or empty for all)
MIN_LANGUAGE_CONFIDENCE=0.5    # Minimum confidence for language detection (0-1)

# Optional: Trend Lifecycle Management
TREND_EXPIRATION_DAYS=30       # Archive trends older than N days (default: 30)
TREND_INACTIVE_DAYS=14        # Apply decay to trends inactive for N days (default: 14)
TREND_DECAY_ENABLED=true      # Enable engagement score decay (default: true)
TREND_DECAY_RATE=0.05         # Decay rate per week (default: 0.05 = 5%)
TREND_ARCHIVE_ENABLED=true    # Archive instead of delete expired trends (default: true)
```

### Direct Configuration (Alternative)

Edit the `Config` class in `main.py`:

```python
class Config:
    USERNAME: str = os.getenv("INSTAGRAM_USERNAME", "your_username")
    PASSWORD: str = os.getenv("INSTAGRAM_PASSWORD", "your_password")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL") or "your_supabase_url"
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or "your_supabase_key"
    # ... other settings
```

## 🗄️ Database Setup

### Supabase Table Schema

Create the `instagram` table in your Supabase database using this exact schema:

```sql
create table public.instagram (
  id bigserial not null,
  platform text not null,
  topic_hashtag text not null,
  engagement_score double precision null,
  sentiment_polarity double precision null,
  sentiment_label text null,
  posts bigint null,
  views bigint null,
  metadata jsonb null,
  scraped_at timestamp with time zone null default now(),
  version_id uuid not null,
  constraint instagram_pkey primary key (id),
  constraint instagram_sentiment_label_check check (
    (
      sentiment_label = any (
        array[
          'positive'::text,
          'negative'::text,
          'neutral'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

-- Indexes for performance
create index idx_instagram_platform on public.instagram using btree (platform);
create index idx_instagram_hashtag on public.instagram using btree (topic_hashtag);
create index idx_instagram_scraped_at on public.instagram using btree (scraped_at);
create index idx_instagram_version_id on public.instagram using btree (version_id);
create index idx_instagram_sentiment on public.instagram using btree (sentiment_label);
create index idx_instagram_metadata on public.instagram using gin (metadata);
```

### Metadata Structure

The `metadata` JSONB field contains:
```json
{
  "url": "https://www.instagram.com/explore/tags/hashtag/",
  "hashtags": ["#hashtag"],
  "likes": 1000,
  "comments": 50,
  "views": 50000,
  "language": "en",
  "timestamp": "2024-01-01T12:00:00",
  "version": "version_id",
  "format": "photo",
  "content_types": {
    "photo": 2,
    "reel": 1
  },
  "language_summary": {
    "primary_language": "en",
    "primary_language_percent": 100.0,
    "distribution": {"en": 3}
  },
  "sentiment_summary": {
    "overall_label": "positive",
    "positive": 2,
    "neutral": 1,
    "negative": 0
  },
  "raw_blob": {
    "primary_format": "photo",
    "content_types": {"photo": 2, "reel": 1},
    "posts_count": 3,
    "video_count": 0
  }
}
```

## 🚀 Usage

### Run Once (Test Mode)
```bash
python main.py --run-once
```

This will:
- Discover trending hashtags from Explore page
- Analyze top 10 hashtags (configurable)
- Extract engagement metrics for 3 posts per hashtag (configurable)
- Detect language and apply filtering if configured
- Save to Supabase using bulk insert
- Export JSON and CSV files
- Run automatic lifecycle cleanup

### Run Continuously (Scheduled)
```bash
python main.py
```

This will:
- Run the scraper every 3 hours (configurable)
- Continue running until stopped
- Handle errors gracefully
- Log all activities

### Manual Login Mode

If automated login fails, the scraper will:
1. Open a browser window (non-headless)
2. Wait for you to manually log in
3. Automatically detect successful login
4. Continue with scraping

## 📊 Output Formats

### Console Output
The scraper provides detailed console output including:
- Discovered hashtags by category
- Engagement metrics per hashtag
- Content type distribution
- Sentiment analysis results
- Language detection results
- Database save status

### JSON Export
Exported as `trends_export_YYYYMMDD_HHMMSS.json`:
```json
{
  "version": "version_id",
  "platform": "Instagram",
  "export_timestamp": "2024-01-01T12:00:00",
  "total_trends": 10,
  "trends": [
    {
      "platform": "Instagram",
      "hashtags": ["#trending"],
      "hashtag": "trending",
      "scores": {
        "engagement_score": 9134.0,
        "likes": 9134,
        "comments": 0,
        "views": 203236,
        "total_engagement": 212370
      },
      "timestamp": "2024-01-01T12:00:00",
      "category": "entertainment",
      "format": "photo",
      "content_types": {"photo": 3},
      "language": "en",
      "sentiment": "neutral"
    }
  ]
}
```

### CSV Export
Exported as `trends_export_YYYYMMDD_HHMMSS.csv` with columns:
- platform, hashtag, hashtags, engagement_score, likes, comments, views, timestamp, version, category, format, language, sentiment, frequency, url, posts_analyzed, video_count, content_types

## 🎯 Content Type Detection

The scraper automatically detects and tags content types:
- **photo** - Regular photo posts
- **reel** - Instagram Reels
- **video** - Regular video posts
- **carousel** - Multi-image carousel posts
- **carousel_video** - Carousel posts with videos

## 🌍 Language Detection & Filtering

### Automatic Language Detection

The scraper analyzes post captions using the `langdetect` library to determine the language of each post. This enables:

- **Caption Analysis**: Extracts and analyzes captions from each post
- **Language Identification**: Detects primary language with confidence scores
- **Language Aggregation**: Calculates primary language and distribution per hashtag
- **Multi-language Support**: Handles 55+ languages including:
  - English (en), Spanish (es), French (fr), German (de), Italian (it)
  - Portuguese (pt), Russian (ru), Chinese (zh), Japanese (ja), Korean (ko)
  - Arabic (ar), Hindi (hi), Turkish (tr), Dutch (nl), Polish (pl)
  - And many more...

### Language Data Structure

**Per Post:**
- `language`: ISO 639-1 language code (e.g., 'en', 'es')
- `language_confidence`: Detection confidence (0-1)
- `language_detected`: Whether detection was successful
- `all_languages`: All detected languages with probabilities

**Per Hashtag (in metadata):**
```json
{
  "language_summary": {
    "primary_language": "en",
    "primary_language_percent": 85.0,
    "primary_language_count": 17,
    "avg_confidence": 0.92,
    "detected_count": 18,
    "total_analyzed": 20,
    "distribution": {
      "en": 17,
      "es": 2,
      "fr": 1
    },
    "detection_rate": 90.0
  }
}
```

### Localized Filtering

Filter trends by specific languages for multi-language client accounts:

**Filter by English only:**
```bash
FILTER_LANGUAGES="en"
ENABLE_LANGUAGE_DETECTION=true
```

**Multi-language support (English, Spanish, French):**
```bash
FILTER_LANGUAGES="en,es,fr"
ENABLE_LANGUAGE_DETECTION=true
```

**No filtering (include all languages):**
```bash
FILTER_LANGUAGES=""  # or don't set it
ENABLE_LANGUAGE_DETECTION=true
```

When `FILTER_LANGUAGES` is configured, only trends with a primary language matching the allowed list will be saved to the database. Trends with other languages will be skipped with a clear message.

### Configuration Options

- **ENABLE_LANGUAGE_DETECTION**: Enable/disable language detection (default: `true`)
- **FILTER_LANGUAGES**: Comma-separated list of allowed language codes (e.g., `"en,es,fr"`). Empty string means no filtering.
- **MIN_LANGUAGE_CONFIDENCE**: Minimum confidence threshold for language detection (default: `0.5` = 50%)

## 🔄 Trend Lifecycle Management

The scraper automatically manages trend lifecycle to prevent database bloat and maintain relevance:

### Expired Trends (>30 days)
- Trends older than 30 days (configurable via `TREND_EXPIRATION_DAYS`) are automatically handled
- **Archive Mode** (default): Trends are marked as `archived` in metadata but not deleted
- **Delete Mode**: Trends are permanently deleted if `TREND_ARCHIVE_ENABLED=false`
- Tracks `archived_at` timestamp and reason

### Inactive Trends (14-30 days)
- Trends not seen for 14+ days (configurable via `TREND_INACTIVE_DAYS`) get engagement score decay
- **Exponential Decay**: `score * (1 - decay_rate) ^ weeks_inactive`
- **Default Decay Rate**: 5% per week (configurable via `TREND_DECAY_RATE`)
- **Minimum Score**: Never goes below 10% of original score
- Helps prioritize active trends in search results

### Lifecycle States
- **Active**: < 14 days since last seen (no action)
- **Inactive**: 14-30 days since last seen (decay applied)
- **Expired**: > 30 days since last seen (archived/deleted)

### Automatic Cleanup
- Runs automatically after each scraper run
- Processes all trends in database
- Provides detailed statistics (archived, deleted, decayed counts)
- Error handling ensures scraper continues even if cleanup fails

### Configuration
```bash
TREND_EXPIRATION_DAYS=30       # When to expire trends
TREND_INACTIVE_DAYS=14        # When to start decay
TREND_DECAY_ENABLED=true      # Enable/disable decay
TREND_DECAY_RATE=0.05         # 5% decay per week
TREND_ARCHIVE_ENABLED=true    # Archive vs delete
```

## 📈 Categories

Hashtags are automatically categorized into:
- **fashion** - Style, outfits, beauty, makeup
- **fitness** - Gym, workout, health, yoga
- **food** - Cooking, recipes, restaurants
- **travel** - Vacation, adventure, tourism
- **technology** - Tech, gadgets, coding, AI
- **business** - Entrepreneurship, startups, finance
- **entertainment** - Movies, music, celebrities, memes
- **lifestyle** - Daily life, inspiration, photography
- **photography** - Photos, cameras, art
- **sports** - Football, basketball, athletics
- **general** - Uncategorized hashtags

## 🔧 Advanced Configuration

### Proxy Configuration
```python
# In Config class
PROXY_URL: Optional[str] = os.getenv("PROXY_URL")
PROXY_USERNAME: Optional[str] = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD: Optional[str] = os.getenv("PROXY_PASSWORD")
```

### Headless Mode
```bash
# Run in headless mode (no browser window)
HEADLESS=true python main.py

# Or in CI/CD
CI=true python main.py
```

### Custom Schedule
Edit the scheduler configuration in `main.py`:
```python
scheduler.add_job(
    run_scraper_job,
    CronTrigger(hours=Config.SCHEDULE_HOURS),
    id='instagram_scraper',
    replace_existing=True
)
```

## 🐛 Troubleshooting

### Login Issues
- **Automated login fails**: The scraper will automatically fall back to manual login
- **Challenge page**: Instagram may show a verification page - complete it manually
- **Account locked**: Check Instagram account status, may need to verify via email/SMS

### No Posts Found
- Instagram may have changed their page structure
- Try running again after a few minutes
- Check if Instagram is blocking your IP (use proxy)

### Database Errors
- Verify Supabase credentials are correct
- Check table schema matches the expected structure
- Ensure database has proper permissions

### Encoding Issues (Windows)
The scraper automatically handles Unicode encoding on Windows. If you see encoding errors:
```bash
# Set environment variable
set PYTHONIOENCODING=utf-8
```

## 📝 Logging

Logs are written to:
- **Console**: Real-time output with emojis and formatting
- **File**: `instagram_scraper.log` (detailed logs)

Log levels:
- **INFO**: General information about scraper progress
- **WARNING**: Non-critical issues
- **ERROR**: Errors that may affect functionality
- **DEBUG**: Detailed debugging information

## 🔒 Security Best Practices

1. **Never commit credentials**: Use environment variables or `.env` file (in `.gitignore`)
2. **Use environment variables**: Prefer environment variables over hardcoded values
3. **Rotate credentials**: Regularly update Instagram and Supabase credentials
4. **Use proxies**: Consider using proxies for enhanced privacy
5. **Rate limiting**: The scraper includes built-in rate limiting to avoid detection

## 📦 Dependencies

Key dependencies:
- **playwright** - Browser automation and web scraping
- **supabase** - Database client for storing trend data
- **textblob** - Sentiment analysis (polarity detection)
- **vaderSentiment** - Advanced sentiment analysis (compound scores)
- **langdetect** - Language detection from text (55+ languages)
- **apscheduler** - Task scheduling for automated runs
- **apscheduler** - Task scheduling for automated runs

See `requirements.txt` for complete list.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

Proprietary - All rights reserved

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section
2. Review log files
3. Check Supabase database status
4. Verify Instagram account status

## ✅ Completed Features

- ✅ Automatic trending hashtag discovery
- ✅ Real engagement metrics extraction (likes, comments, views)
- ✅ Content type detection (photo, reel, video, carousel)
- ✅ Sentiment analysis (TextBlob + VADER)
- ✅ Language detection from captions (langdetect)
- ✅ Localized filtering for multi-language accounts
- ✅ Trend lifecycle management (expire, archive, decay)
- ✅ Bulk database operations with retry mechanisms
- ✅ Structured data exports (JSON, CSV)
- ✅ Proxy support
- ✅ Scheduled automation
- ✅ Manual login fallback

## 🎉 Future Enhancements

- [ ] Multi-account support
- [ ] Real-time notifications
- [ ] Web dashboard
- [ ] API endpoints
- [ ] Enhanced analytics dashboard
- [ ] Custom category definitions

---

**Version**: 1.0.0  
**Last Updated**: November 2024  
**Author**: Instagram Scraper Team
