# Code Logic and Architecture Documentation

## Overview

Your Instagram scraper is a **comprehensive trending hashtag discovery and analysis system** that:
1. Discovers trending hashtags from Instagram's Explore page
2. Extracts real engagement metrics from posts
3. Performs sentiment and language analysis
4. Stores normalized data in Supabase
5. Manages trend lifecycle (archiving, decay)

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN ENTRY POINT                          │
│                   main() / run_scraper_job()                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼────────┐            ┌────────▼────────┐
│  Single Run    │            │  Scheduled Run  │
│  (--run-once)  │            │  (APScheduler)  │
└───────┬────────┘            └────────┬────────┘
        │                               │
        └───────────────┬───────────────┘
                        │
            ┌───────────▼───────────┐
            │   run_scraper_job()   │
            │  (Main Orchestrator)  │
            └───────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  1. Setup    │ │  2. Login   │ │  3. Scrape │
│  Browser &   │ │  Instagram  │ │  & Analyze │
│  Supabase    │ │             │ │            │
└───────┬──────┘ └──────┬──────┘ └─────┬──────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
            ┌───────────▼───────────┐
            │  4. Save to Database  │
            │  5. Lifecycle Cleanup │
            └───────────────────────┘
```

## Detailed Workflow

### Phase 1: Initialization (`run_scraper_job()`)

**Location**: `main.py` line ~3815

**Logic Flow:**
```python
1. Validate configuration (Config.validate())
   ├─ Check Instagram credentials
   ├─ Check Supabase credentials
   └─ Validate scraping parameters

2. Generate unique version ID (UUID)
   └─ Tracks this scraper run

3. Setup observability
   ├─ Set request ID
   ├─ Start trace
   └─ Initialize metrics

4. Initialize Playwright browser
   ├─ Configure proxy (if provided)
   ├─ Set viewport size
   └─ Create browser context

5. Connect to Supabase
   └─ Create Supabase client
```

### Phase 2: Authentication (`login_instagram()`)

**Location**: `main.py` line ~550

**Logic Flow:**
```python
1. Navigate to Instagram login page
   └─ Handle navigation errors with retry

2. Handle cookie consent
   └─ Dismiss cookie banners

3. Find login form elements
   ├─ Multiple selector strategies for username field
   ├─ Find password field
   └─ Handle dynamic React components

4. Enter credentials
   ├─ Human-like typing delays
   └─ Submit form

5. Verify login success
   ├─ Check for home indicators
   ├─ Verify URL changes
   └─ Handle verification challenges

6. Dismiss popups
   └─ "Not Now" buttons, notifications

7. Fallback to manual login (if automated fails)
   └─ Wait for user to manually log in
```

**Key Features:**
- Multiple fallback strategies for finding form elements
- Handles React/JavaScript-heavy pages
- Graceful error handling with manual login fallback
- Anti-detection measures (delays, human-like behavior)

### Phase 3: Hashtag Discovery (`discover_trending_hashtags()`)

**Location**: `main.py` line ~2027

**Logic Flow:**
```python
1. Navigate to Instagram Explore page (/explore/)
   ├─ Handle navigation errors
   └─ Retry logic if navigation fails

2. Wait for page to load
   ├─ Wait for body element
   ├─ Wait for React to render
   └─ Handle network idle state

3. Dismiss blocking popups
   └─ "Turn on Notifications", etc.

4. Scroll to load more posts
   ├─ Scroll SCROLL_COUNT times (default: 15)
   ├─ Wait between scrolls
   └─ Collect posts as they load

5. Extract post links
   ├─ Find all post links (a[href*='/p/'], a[href*='/reel/'])
   ├─ Deduplicate posts
   └─ Store post URLs

6. Extract hashtags from posts
   ├─ Visit each post (or extract from link previews)
   ├─ Find hashtag links (a[href*='/explore/tags/'])
   └─ Count hashtag frequency

7. Categorize hashtags
   └─ categorize_hashtag() function
      ├─ Fashion, Fitness, Food, Travel, etc.
      └─ Returns category name

8. Select top hashtags
   ├─ Filter by minimum frequency
   ├─ Sort by frequency
   └─ Take top N hashtags (TOP_HASHTAGS_TO_SAVE)

9. Build hashtag data structure
   ├─ hashtag name
   ├─ frequency count
   ├─ sample posts (for engagement analysis)
   └─ category
```

**Key Features:**
- Handles dynamic content loading
- Multiple strategies for finding posts
- Frequency-based ranking
- Automatic categorization

### Phase 4: Engagement Analysis (`analyze_hashtag_engagement()`)

**Location**: `main.py` line ~2610

**Logic Flow:**
```python
For each hashtag:
    1. Get sample posts (default: 3 posts per hashtag)
    
    2. For each sample post:
        a. Call get_post_engagement(post_url)
           ├─ Navigate to post
           ├─ Extract likes
           ├─ Extract comments
           ├─ Extract views (for videos/reels)
           ├─ Extract caption
           ├─ Detect content type (photo/reel/video)
           ├─ Detect language (langdetect)
           └─ Analyze sentiment (TextBlob + VADER)
        
        b. Collect engagement data
    
    3. Aggregate across all posts:
        ├─ Calculate averages (avg_likes, avg_comments, avg_engagement)
        ├─ Aggregate sentiment (positive/neutral/negative counts)
        ├─ Aggregate language (distribution, primary language)
        ├─ Aggregate content types (photo/reel/video distribution)
        └─ Calculate total engagement
    
    4. Return aggregated summary
```

**Key Features:**
- Real engagement metrics extraction
- Multi-post aggregation
- Sentiment analysis
- Language detection
- Content type distribution

### Phase 5: Engagement Extraction (`get_post_engagement()`)

**Location**: `main.py` line ~1726

**Logic Flow:**
```python
1. Navigate to post URL
   └─ Handle navigation errors

2. Detect content type
   ├─ Check URL for /reel/ or /p/
   ├─ Check for video indicators
   └─ Return: 'photo', 'reel', 'video', 'carousel'

3. Extract views (if video/reel)
   ├─ Multiple selector strategies
   ├─ Parse K/M suffixes (5.2K → 5200, 1.2M → 1200000)
   └─ Handle different Instagram formats

4. Extract likes
   ├─ Multiple selector strategies
   ├─ Parse K/M suffixes
   └─ Fallback to element counting

5. Extract comments
   ├─ Multiple selector strategies
   ├─ Parse K/M suffixes
   └─ Fallback to counting visible elements

6. Extract caption
   ├─ Multiple selector strategies
   ├─ Clean hashtags and mentions
   └─ Limit length

7. Analyze caption
   ├─ Language detection (langdetect)
   │  ├─ ISO 639-1 code
   │  ├─ Confidence score
   │  └─ All detected languages
   └─ Sentiment analysis
      ├─ TextBlob polarity
      ├─ VADER sentiment (if available)
      └─ Combined score

8. Return engagement data structure
```

**Key Features:**
- Multiple extraction strategies (robust to UI changes)
- Handles K/M number suffixes
- Fallback values if extraction fails
- Comprehensive metadata collection

### Phase 6: Data Normalization (`create_trend_record()`)

**Location**: `main.py` line ~2900+

**Logic Flow:**
```python
1. Take aggregated engagement data
2. Create TrendRecord dataclass:
   ├─ platform: "Instagram"
   ├─ url: hashtag URL
   ├─ hashtags: [list of hashtags]
   ├─ likes: average likes
   ├─ comments: average comments
   ├─ views: average views
   ├─ language: primary language (ISO 639-1)
   ├─ timestamp: current time
   ├─ engagement_score: avg_engagement
   ├─ version: VERSION_ID
   └─ raw_blob: {
       ├─ sentiment_summary
       ├─ language_summary
       ├─ content_types
       └─ all aggregated data
   }
```

### Phase 7: Database Storage (`save_trends_to_database()`)

**Location**: `main.py` line ~3650+

**Logic Flow:**
```python
1. For each hashtag:
   ├─ Analyze engagement (analyze_hashtag_engagement)
   ├─ Create TrendRecord
   └─ Add to batch

2. Bulk insert to Supabase
   ├─ Check existing records
   ├─ Separate new inserts vs updates
   ├─ Bulk insert new records
   │  ├─ Retry with exponential backoff
   │  └─ Fallback to individual inserts
   └─ Update existing records individually

3. Handle errors
   ├─ Track success/failure counts
   └─ Log errors with error codes
```

**Key Features:**
- Bulk operations for efficiency
- Retry logic with exponential backoff
- Fallback to individual inserts
- Lifecycle tracking (first_seen, last_seen)

### Phase 8: Lifecycle Management (`cleanup_old_trends()`)

**Location**: `main.py` line ~3290+

**Logic Flow:**
```python
1. Get all trends from database

2. For each trend:
   ├─ Calculate days since last seen
   ├─ Apply engagement score decay (if inactive > 14 days)
   │  └─ Decay formula: score * (1 - decay_rate) ^ weeks_inactive
   └─ Archive or delete (if older than 30 days)

3. Update database
   └─ Save decayed scores, archive status
```

## Key Data Structures

### TrendRecord
```python
@dataclass
class TrendRecord:
    platform: str              # "Instagram"
    url: str                   # Hashtag URL
    hashtags: List[str]        # List of hashtags
    likes: int                 # Average likes
    comments: int              # Average comments
    views: int                 # Average views
    language: str              # ISO 639-1 code
    timestamp: datetime        # Scrape timestamp
    engagement_score: float    # Calculated score
    version: str               # Version ID
    raw_blob: Dict[str, Any]   # All aggregated data
```

### Engagement Data
```python
{
    'likes': 1234,
    'comments': 56,
    'views': 50000,           # For videos/reels
    'total_engagement': 1290, # likes + comments
    'is_video': True,
    'format': 'reel',
    'caption': 'Post caption text',
    'language': 'en',
    'language_confidence': 0.95,
    'language_detected': True,
    'sentiment': {
        'polarity': 0.15,
        'label': 'positive',
        'emoji': '😊',
        'combined_score': 0.2
    }
}
```

### Hashtag Data
```python
{
    'hashtag': 'trending',
    'frequency': 5,           # Times seen across posts
    'posts_count': 10,        # Total posts using hashtag
    'sample_posts': [        # Post URLs for analysis
        '/p/ABC123/',
        '/p/DEF456/',
        '/p/GHI789/'
    ],
    'category': 'fashion'    # Auto-categorized
}
```

## Key Algorithms

### 1. Engagement Score Calculation

```python
# Per post:
total_engagement = likes + comments

# Per hashtag (trend):
engagement_score = average(total_engagement across all sample posts)
```

**Example:**
- Post 1: 1000 likes + 50 comments = 1050 engagement
- Post 2: 2000 likes + 100 comments = 2100 engagement
- Post 3: 1500 likes + 75 comments = 1575 engagement
- **Trend Score**: (1050 + 2100 + 1575) / 3 = **1575.0**

### 2. Hashtag Frequency Analysis

```python
1. Collect all posts from Explore page
2. Extract hashtags from each post
3. Count occurrences: hashtag_counter[hashtag] += 1
4. Filter: frequency >= MIN_HASHTAG_FREQUENCY
5. Sort by frequency (descending)
6. Take top N: TOP_HASHTAGS_TO_SAVE
```

### 3. Sentiment Aggregation

```python
For each post:
    sentiment = analyze_sentiment(caption)
    # Returns: {'polarity': 0.15, 'label': 'positive', ...}

Aggregate:
    sentiment_counts = {
        'positive': count of positive posts,
        'neutral': count of neutral posts,
        'negative': count of negative posts
    }
    avg_polarity = average(all polarities)
    overall_label = most_common label
```

### 4. Language Distribution

```python
For each post:
    language_info = detect_language(caption)
    # Returns: {'language': 'en', 'confidence': 0.95, ...}

Aggregate:
    language_distribution = Counter()
    # Count: {'en': 17, 'es': 3}
    
    primary_language = most_common language
    primary_language_percent = (count / total) * 100
    avg_confidence = average confidence for primary language
```

### 5. Engagement Score Decay

```python
days_inactive = (now - last_seen).days
weeks_inactive = days_inactive / 7

if days_inactive > 14:  # TREND_INACTIVE_DAYS
    decay_rate = 0.05  # 5% per week (TREND_DECAY_RATE)
    decayed_score = original_score * ((1 - decay_rate) ** weeks_inactive)
    min_score = original_score * 0.1  # Never go below 10%
    decayed_score = max(decayed_score, min_score)
```

## Error Handling Strategy

### 1. Navigation Errors
- **Retry logic**: Try navigation up to 2 times
- **Fallback**: Check if already on correct page
- **Error codes**: `SCRAPE_NAVIGATION_FAILED`

### 2. Element Not Found
- **Multiple selectors**: Try different CSS selectors
- **Fallback values**: Use estimated values if extraction fails
- **Error codes**: `SCRAPE_ELEMENT_NOT_FOUND`

### 3. Proxy Failures
- **Error detection**: Check for proxy-related errors
- **Error codes**: `PROXY_CONNECTION_FAILED`, `PROXY_TIMEOUT`
- **Metrics**: Track proxy failures

### 4. Database Errors
- **Retry with backoff**: Exponential backoff (2s, 4s, 6s)
- **Fallback**: Individual inserts if bulk fails
- **Error codes**: `DB_INSERT_ERROR`, `DB_CONNECTION_ERROR`

## Observability Integration

### Structured Logging
- **JSON format**: All logs in structured JSON
- **Request/Trace IDs**: Track operations end-to-end
- **Error codes**: Categorized error taxonomy

### Metrics Collection
- **Counters**: Request counts, error counts, job counts
- **Histograms**: Request duration, operation duration
- **Labels**: Platform, adapter, outcome, error type

### Event Tracing
- **Start trace**: `logger.start_trace('operation_name')`
- **End trace**: `logger.end_trace('operation_name', success=True)`
- **Duration tracking**: Automatic duration calculation

## Configuration System

### Environment Variables
```python
# Credentials
INSTAGRAM_USERNAME
INSTAGRAM_PASSWORD
SUPABASE_URL
SUPABASE_KEY

# Scraping Parameters
SCROLL_COUNT = 15              # Times to scroll Explore page
POSTS_TO_SCAN = 400            # Max posts to analyze
MIN_HASHTAG_FREQUENCY = 1      # Min occurrences to include
TOP_HASHTAGS_TO_SAVE = 10      # Top N hashtags to save
POSTS_PER_HASHTAG = 3          # Sample posts per hashtag

# Proxy
PROXY_SERVER
PROXY_USERNAME
PROXY_PASSWORD

# Language
ENABLE_LANGUAGE_DETECTION = true
FILTER_LANGUAGES = "en,es,fr"  # Comma-separated
MIN_LANGUAGE_CONFIDENCE = 0.5

# Scheduling
SCHEDULE_HOURS = 3             # Run every N hours

# Lifecycle
TREND_EXPIRATION_DAYS = 30
TREND_INACTIVE_DAYS = 14
TREND_DECAY_ENABLED = true
TREND_DECAY_RATE = 0.05

# Observability
USE_JSON_LOGGING = true
LOG_LEVEL = INFO
```

## Scheduling System

### APScheduler Integration
```python
scheduler = BlockingScheduler()
scheduler.add_job(
    run_scraper_job,
    trigger=CronTrigger(hour=f'*/{SCHEDULE_HOURS}'),
    id='instagram_scraper_job'
)
scheduler.start()
```

**Modes:**
- **Scheduled**: Runs every N hours automatically
- **Single Run**: `python main.py --run-once` for testing

## Data Flow Summary

```
1. Start Job
   ↓
2. Login to Instagram
   ↓
3. Navigate to /explore/
   ↓
4. Scroll & Collect Posts
   ↓
5. Extract Hashtags & Count Frequency
   ↓
6. Select Top Hashtags
   ↓
7. For Each Hashtag:
   ├─ Visit Sample Posts
   ├─ Extract Engagement Metrics
   ├─ Analyze Sentiment
   ├─ Detect Language
   └─ Aggregate Data
   ↓
8. Create TrendRecord Objects
   ↓
9. Bulk Insert to Supabase
   ↓
10. Lifecycle Cleanup (Decay, Archive)
    ↓
11. Export to JSON/CSV
    ↓
12. End Job
```

## Key Design Patterns

### 1. Adapter Pattern (Potential)
- Base scraper interface (for future multi-platform)
- Platform-specific implementations

### 2. Retry Pattern
- Exponential backoff
- Maximum retry attempts
- Fallback strategies

### 3. Fallback Pattern
- Multiple selector strategies
- Estimated values if extraction fails
- Graceful degradation

### 4. Observer Pattern (Observability)
- Metrics collection
- Event tracing
- Structured logging

### 5. Strategy Pattern
- Multiple extraction strategies
- Platform-specific strategies
- Configurable strategies

## Performance Optimizations

1. **Bulk Operations**: Batch database inserts
2. **Parallel Processing**: Could parallelize post analysis (future)
3. **Caching**: Cache language detection results
4. **Lazy Loading**: Only load what's needed
5. **Connection Pooling**: Reuse Supabase connections

## Security & Compliance

1. **No PII Collection**: Only public content
2. **Rate Limiting**: Delays between requests
3. **User Agent**: Appropriate user agents
4. **Error Handling**: Don't expose sensitive data in errors
5. **Environment Variables**: Credentials in env vars, not code

## Future Extension Points

1. **Multi-Platform**: Add TikTok, Twitter adapters
2. **Proxy Rotation**: Implement proxy pool manager
3. **Async Processing**: Use async/await for parallel scraping
4. **Caching Layer**: Redis for frequently accessed data
5. **API Endpoints**: REST API for querying trends
6. **Real-time Updates**: WebSocket for live trend updates

## Summary

Your code implements a **complete trending hashtag discovery and analysis pipeline**:

1. **Discovery**: Finds trending hashtags from Explore page
2. **Analysis**: Extracts real engagement metrics
3. **Enrichment**: Adds sentiment and language analysis
4. **Storage**: Saves to Supabase with lifecycle management
5. **Observability**: Comprehensive logging and metrics
6. **Automation**: Scheduled runs with APScheduler

The system is **robust** (multiple fallbacks), **observable** (structured logging, metrics), and **maintainable** (clear separation of concerns, error handling).

