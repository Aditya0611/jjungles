# Daily Snapshots & Versioning Guide

## Overview

Daily snapshot/versioning enables trend comparison over time by:
- **Daily Snapshots**: Each scrape run creates a snapshot for the current date
- **Versioning**: Multiple snapshots per day are versioned (1, 2, 3...)
- **Trend Comparison**: Compare trends across different days and analyze changes

## Features

### 1. Automatic Daily Snapshots
- Each scrape run automatically creates a snapshot for the current date
- Snapshot date is set to `YYYY-MM-DD` format (UTC date)
- Version number increments automatically (1, 2, 3... per day)

### 2. Version Tracking
- First run of the day = version 1
- Second run of the day = version 2
- And so on...
- Enables tracking changes throughout the day

### 3. Trend Comparison
- Compare trends between any two dates
- Track trending up/down hashtags
- Identify new trends and disappeared trends
- Analyze trend history over multiple days

## Database Schema

### Migration: `006_add_daily_snapshots.sql`

Adds two columns:
- `snapshot_date` (DATE): Date when snapshot was taken
- `snapshot_version` (INTEGER): Version number within the day

### Indexes Created:
- `idx_tiktok_snapshot_date`: Fast queries by date
- `idx_tiktok_snapshot_topic`: Trend tracking by date + topic
- `idx_tiktok_snapshot_engagement`: Daily rankings
- `idx_tiktok_snapshot_version`: Version tracking

### Views Created:
- `tiktok_daily_latest`: Latest version per day per topic
- `tiktok_daily_summary`: Daily summary statistics

## Usage

### Automatic (Default)

The scraper automatically creates daily snapshots:

```python
# Just run the scraper - snapshots are created automatically
python base.py
```

Each run will:
1. Get current date (UTC)
2. Query for max version for that date
3. Set version = max + 1 (or 1 if first run)
4. Include `snapshot_date` and `snapshot_version` in all records

### Manual Control

```python
from base import upload_to_supabase, init_supabase

supabase = init_supabase()

# Disable daily snapshots
upload_to_supabase(
    supabase,
    scraped_data,
    enable_daily_snapshots=False  # Disable snapshots
)
```

## Trend Comparison Functions

### Get Daily Snapshot

```python
from trend_comparison import get_daily_snapshot

# Get latest snapshot for a date
snapshot = get_daily_snapshot(supabase, "tiktok", "2024-01-15")

# Get specific version
snapshot = get_daily_snapshot(supabase, "tiktok", "2024-01-15", version=2)
```

### Compare Two Days

```python
from trend_comparison import compare_daily_snapshots

# Compare trends between two dates
comparisons = compare_daily_snapshots(
    supabase, 
    "tiktok",
    "2024-01-15",  # Date 1
    "2024-01-16"   # Date 2
)

# Results include:
# - score_change: Difference in engagement scores
# - score_change_percent: Percentage change
# - trend_direction: "rising", "falling", or "stable"
```

### Get Trending Up Hashtags

```python
from trend_comparison import get_trending_up

# Get hashtags trending up between two dates
trending_up = get_trending_up(
    supabase,
    "tiktok",
    "2024-01-15",
    "2024-01-16",
    min_change=1.0  # Minimum score increase
)
```

### Get Trending Down Hashtags

```python
from trend_comparison import get_trending_down

trending_down = get_trending_down(
    supabase,
    "tiktok",
    "2024-01-15",
    "2024-01-16",
    min_change=1.0  # Minimum score decrease
)
```

### Get New Trends

```python
from trend_comparison import get_new_trends

# Hashtags that appeared in date2 but not in date1
new_trends = get_new_trends(
    supabase,
    "tiktok",
    "2024-01-15",
    "2024-01-16"
)
```

### Get Disappeared Trends

```python
from trend_comparison import get_disappeared_trends

# Hashtags that were in date1 but not in date2
disappeared = get_disappeared_trends(
    supabase,
    "tiktok",
    "2024-01-15",
    "2024-01-16"
)
```

### Get Trend History

```python
from trend_comparison import get_trend_history

# Get 7-day history for a specific hashtag
history = get_trend_history(
    supabase,
    "tiktok",
    "#viral",
    days=7
)
```

### Get Daily Summary

```python
from trend_comparison import get_daily_summary

# Get summary for a specific date
summary = get_daily_summary(supabase, "tiktok", "2024-01-15")

# Get summary for today
summary = get_daily_summary(supabase, "tiktok")
```

## SQL Queries

### Get Latest Snapshot for Today

```sql
SELECT *
FROM public.tiktok
WHERE snapshot_date = CURRENT_DATE
  AND snapshot_version = (
    SELECT MAX(snapshot_version) 
    FROM public.tiktok 
    WHERE snapshot_date = CURRENT_DATE
  )
ORDER BY engagement_score DESC
LIMIT 20;
```

### Compare Trends Across Two Dates

```sql
SELECT 
    t1.topic,
    t1.engagement_score as score_date1,
    t2.engagement_score as score_date2,
    (t2.engagement_score - t1.engagement_score) as score_change,
    t1.snapshot_date as date1,
    t2.snapshot_date as date2
FROM public.tiktok t1
JOIN public.tiktok t2 ON t1.topic = t2.topic
WHERE t1.snapshot_date = '2024-01-15'
  AND t2.snapshot_date = '2024-01-16'
  AND t1.snapshot_version = (
    SELECT MAX(snapshot_version) 
    FROM public.tiktok 
    WHERE snapshot_date = t1.snapshot_date AND topic = t1.topic
  )
  AND t2.snapshot_version = (
    SELECT MAX(snapshot_version) 
    FROM public.tiktok 
    WHERE snapshot_date = t2.snapshot_date AND topic = t2.topic
  )
ORDER BY score_change DESC;
```

### Track Trend Growth Over 7 Days

```sql
SELECT 
    snapshot_date,
    topic,
    engagement_score,
    LAG(engagement_score) OVER (PARTITION BY topic ORDER BY snapshot_date) as previous_score,
    engagement_score - LAG(engagement_score) OVER (PARTITION BY topic ORDER BY snapshot_date) as score_delta
FROM public.tiktok
WHERE topic = '#viral'
  AND snapshot_date >= CURRENT_DATE - INTERVAL '7 days'
  AND snapshot_version = (
    SELECT MAX(snapshot_version) 
    FROM public.tiktok t2
    WHERE t2.snapshot_date = tiktok.snapshot_date 
      AND t2.topic = tiktok.topic
  )
ORDER BY snapshot_date DESC;
```

### Get Daily Summary Statistics

```sql
SELECT 
    snapshot_date,
    COUNT(DISTINCT topic) as unique_hashtags,
    AVG(engagement_score) as avg_engagement_score,
    MAX(engagement_score) as max_engagement_score,
    MIN(engagement_score) as min_engagement_score,
    COUNT(*) as total_records,
    MAX(snapshot_version) as latest_version
FROM public.tiktok
WHERE snapshot_date IS NOT NULL
GROUP BY snapshot_date
ORDER BY snapshot_date DESC;
```

## Example: Daily Trend Report

```python
from base import init_supabase
from trend_comparison import (
    get_daily_summary,
    compare_daily_snapshots,
    get_trending_up,
    get_new_trends
)
from datetime import date, timedelta

supabase = init_supabase()
today = date.today().isoformat()
yesterday = (date.today() - timedelta(days=1)).isoformat()

# Get today's summary
summary = get_daily_summary(supabase, "tiktok", today)
print(f"Today's Snapshot: {summary['total_hashtags']} hashtags, avg score: {summary['avg_engagement_score']:.2f}")

# Compare with yesterday
comparisons = compare_daily_snapshots(supabase, "tiktok", yesterday, today)

# Get trending up
trending_up = get_trending_up(supabase, "tiktok", yesterday, today, min_change=1.0)
print(f"\nTrending Up ({len(trending_up)} hashtags):")
for item in trending_up[:5]:
    print(f"  {item['topic']}: {item['score_date1']:.1f} → {item['score_date2']:.1f} (+{item['score_change']:.1f})")

# Get new trends
new = get_new_trends(supabase, "tiktok", yesterday, today)
print(f"\nNew Trends ({len(new)} hashtags):")
for item in new[:5]:
    print(f"  {item['topic']}: Score {item['score_date2']:.1f}")
```

## Benefits

1. **Historical Analysis**: Track how trends change over time
2. **Daily Comparisons**: Compare trends between any two days
3. **Version Tracking**: Multiple snapshots per day for intraday analysis
4. **Trend Detection**: Automatically identify rising/falling trends
5. **Data Integrity**: Each snapshot is versioned and timestamped

## Migration

Run the migration to add snapshot support:

```sql
-- In Supabase SQL Editor, run:
-- migrations/006_add_daily_snapshots.sql
```

This adds:
- `snapshot_date` column
- `snapshot_version` column
- Indexes for efficient queries
- Views for common queries

---

**Status**: ✅ Implemented
**Files**: `migrations/006_add_daily_snapshots.sql`, `trend_comparison.py`, `base.py` (updated)

