# Cross-Platform Hashtag Scraper - Architecture

## Overview

This project implements a cross-platform hashtag scraping system that supports multiple social media platforms. The architecture is designed to be extensible, allowing easy addition of new platforms.

## Architecture

### Base Classes

- **`BaseHashtagScraper`** (`base_scraper.py`): Abstract base class that defines the interface for all platform scrapers
  - Common functionality: hashtag extraction, sentiment analysis, result saving
  - Abstract methods: `login()`, `navigate_to_feed()`, `scroll_and_collect_hashtags()`, `close()`

### Platform Implementations

- **`LinkedInHashtagScraper`** (`linkedin_scraper.py`): Full implementation for LinkedIn
- **`InstagramHashtagScraper`** (`instagram_scraper.py`): Stub for Sprint 1
- **`TwitterHashtagScraper`** (`twitter_scraper.py`): Stub for Sprint 1
- **`TikTokHashtagScraper`** (`tiktok_scraper.py`): Stub for Sprint 1
- **`FacebookHashtagScraper`** (`facebook_scraper.py`): Stub for Sprint 1

### Platform Manager

- **`PlatformManager`** (`platform_manager.py`): Manages multiple platform scrapers
  - Creates and manages scraper instances
  - Coordinates multi-platform scraping
  - Combines results from all platforms

## Sprint 1 Status

✅ **Completed & Ready for Delivery:**
- Base scraper architecture and modular utility system
- **LinkedIn** full production-grade implementation
- Platform manager and cross-platform result aggregation
- Automated Supabase integration for unified trending data
- Odoo module for frequency configuration and monitoring

🚧 **Stubs (Planned for Future Sprints):**
- Instagram scraper (Stub exists)
- Twitter/X scraper (Stub exists)
- TikTok scraper (Stub exists)
- Facebook scraper (Stub exists)

## Usage Examples

### Single Platform
```python
from linkedin_scraper import LinkedInHashtagScraper

scraper = LinkedInHashtagScraper(use_supabase=True)
scraper.login()
scraper.navigate_to_feed()
scraper.scroll_and_collect_hashtags(max_scrolls=30)
scraper.print_results()
scraper.save_results()
scraper.close()
```

### Multiple Platforms
```python
from platform_manager import PlatformManager

manager = PlatformManager(use_supabase=True)

# Scrape LinkedIn
manager.scrape_platform('linkedin', max_scrolls=30)

# Scrape Instagram (stub - returns empty results)
manager.scrape_platform('instagram', max_scrolls=30)

# Scrape multiple platforms
manager.scrape_multiple_platforms(
    ['linkedin', 'instagram', 'twitter'],
    max_scrolls=30
)

# Get combined results
combined = manager.get_combined_results()
```

### Command Line
```bash
# Single platform
python scrape_all_platforms.py --platforms linkedin

# Multiple platforms
python scrape_all_platforms.py --platforms linkedin instagram twitter

# All platforms
python scrape_all_platforms.py --platforms all

# With options
python scrape_all_platforms.py --platforms linkedin --max-scrolls 50 --scroll-pause 3.0
```

## Adding a New Platform

1. Create a new file: `{platform}_scraper.py`
2. Extend `BaseHashtagScraper`:
```python
from base_scraper import BaseHashtagScraper

class NewPlatformHashtagScraper(BaseHashtagScraper):
    def __init__(self, use_supabase=True):
        super().__init__('newplatform', use_supabase)
    
    def login(self, **kwargs):
        # Implement login
        pass
    
    def navigate_to_feed(self):
        # Implement navigation
        pass
    
    def scroll_and_collect_hashtags(self, max_scrolls=30, scroll_pause_time=2.0):
        # Implement scraping
        pass
    
    def close(self):
        # Implement cleanup
        pass
```

3. Add to `PlatformManager.SUPPORTED_PLATFORMS`:
```python
SUPPORTED_PLATFORMS = {
    ...
    'newplatform': 'newplatform_scraper',
}
```

## Data Structure

All platforms return results in the same format:

```json
{
  "scrape_metadata": {
    "platform": "linkedin",
    "scraped_at": "2024-01-01T00:00:00",
    "version_id": "uuid",
    "total_posts_scanned": 100,
    "scrolls_performed": 30
  },
  "statistics": {
    "total_hashtags_collected": 500,
    "unique_hashtags": 150,
    "average_occurrences": 3.33,
    "top_10_percentage": 45.2
  },
  "top_10_trending_hashtags": [
    {
      "rank": 1,
      "hashtag": "#technology",
      "count": 45,
      "percentage": 9.0,
      "sentiment": "positive"
    }
  ]
}
```

## Supabase Schema

The Supabase **`trends`** table is the unified cross-platform table that stores data from all platforms:

- `platform`: Platform name (linkedin, instagram, twitter, tiktok, facebook)
- `topic_hashtag`: The hashtag
- `engagement_score`: Calculated engagement metric
- `sentiment_polarity`: Sentiment score (-1 to 1)
- `sentiment_label`: positive/negative/neutral
- `posts`: Number of posts containing the hashtag
- `metadata`: Additional JSON data

**Setup:**
Run `unified_trends_schema.sql` in Supabase SQL Editor to create the table.

**Querying:**
```sql
-- Get LinkedIn data
SELECT * FROM public.trends WHERE platform = 'linkedin';

-- Get all platforms
SELECT * FROM public.trends ORDER BY scraped_at DESC;

-- Cross-platform trending hashtags
SELECT topic_hashtag, COUNT(DISTINCT platform) as platform_count
FROM public.trends
GROUP BY topic_hashtag
HAVING COUNT(DISTINCT platform) > 1;
```

## Future Enhancements

- Full Instagram implementation
- Full Twitter/X implementation
- Full TikTok implementation
- Full Facebook implementation
- Real-time scraping
- Scheduled scraping
- API endpoints
- Web dashboard

