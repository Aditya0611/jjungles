# Normalized Schema Guide

## Overview

The normalized schema provides a more structured approach to storing trend data with separate tables for:
- **source**: Platform information
- **trend**: Core trend information
- **trend_version**: Versioned trend data (daily snapshots)
- **metric**: Engagement and performance metrics

## Schema Structure

```
source (platforms)
  └── trend (topics/hashtags)
       └── trend_version (daily snapshots)
            └── metric (posts, views, likes, etc.)
```

## Tables

### 1. source

Stores platform information.

**Columns:**
- `id` - Primary key
- `platform` - Platform identifier (tiktok, instagram, x, linkedin, facebook)
- `display_name` - Display name (TikTok, Instagram, etc.)
- `enabled` - Whether platform is enabled
- `metadata` - Platform-specific metadata

**Indexes:**
- `idx_source_platform` - On platform
- `idx_source_enabled` - On enabled (partial)

### 2. trend

Stores core trend information (one row per unique topic per platform).

**Columns:**
- `id` - Primary key
- `source_id` - Foreign key to source
- `topic` - Original topic/hashtag (e.g., "#viral")
- `normalized_topic` - Normalized topic for deduplication
- `first_discovered_at` - First discovery timestamp
- `last_seen_at` - Most recent sighting
- `status` - Trend status (active, declining, archived)
- `metadata` - Additional trend metadata

**Indexes:**
- `idx_trend_source_id` - On source_id
- `idx_trend_topic` - On topic
- `idx_trend_normalized_topic` - On normalized_topic
- `idx_trend_status` - On status
- `idx_trend_first_discovered` - On first_discovered_at DESC
- `idx_trend_last_seen` - On last_seen_at DESC
- **`idx_trend_source_discovered`** - **Composite on (source_id, first_discovered_at DESC)**

**Unique Constraint:**
- `(source_id, normalized_topic)` - One trend per topic per platform

### 3. trend_version

Stores versioned trend data for daily snapshots.

**Columns:**
- `id` - Primary key
- `trend_id` - Foreign key to trend
- `version_date` - Date of snapshot (YYYY-MM-DD)
- `version_number` - Version number for this date (1, 2, 3...)
- `engagement_score` - Calculated engagement score (1.0-10.0)
- `sentiment_polarity` - Sentiment polarity (-1.0 to 1.0)
- `sentiment_label` - Sentiment label
- `language` - Detected language code (ISO 639-1)
- `language_confidence` - Language detection confidence
- `scraped_at` - Scraping timestamp
- `version_id` - Scraper run session ID
- `metadata` - Additional version metadata

**Indexes:**
- `idx_trend_version_trend_id` - On trend_id
- `idx_trend_version_date` - On version_date DESC
- **`idx_trend_version_engagement`** - **On engagement_score DESC**
- `idx_trend_version_scraped_at` - On scraped_at DESC
- `idx_trend_version_language` - On language (partial)
- `idx_trend_version_sentiment` - On sentiment_label (partial)
- `idx_trend_version_trend_date` - Composite on (trend_id, version_date DESC, version_number DESC)

**Unique Constraint:**
- `(trend_id, version_date, version_number)` - One version per trend per date per version number

### 4. metric

Stores engagement and performance metrics.

**Columns:**
- `id` - Primary key
- `trend_version_id` - Foreign key to trend_version
- `metric_type` - Type: posts, views, likes, shares, comments, followers, engagement_rate, other
- `metric_value` - Metric value (BIGINT)
- `metric_unit` - Unit: count, percentage, etc.
- `collected_at` - Collection timestamp
- `metadata` - Additional metric metadata

**Indexes:**
- `idx_metric_trend_version_id` - On trend_version_id
- `idx_metric_type` - On metric_type
- `idx_metric_collected_at` - On collected_at DESC
- `idx_metric_value` - On metric_value DESC
- `idx_metric_version_type` - Composite on (trend_version_id, metric_type)

## Key Indexes

### 1. (platform, discovered_at)

This is achieved via:
- `idx_trend_source_discovered` on `(source_id, first_discovered_at DESC)`
- Join with `source` table to get platform

**Query Example:**
```sql
SELECT s.platform, t.topic, t.first_discovered_at
FROM trend t
JOIN source s ON t.source_id = s.id
WHERE s.platform = 'tiktok'
ORDER BY t.first_discovered_at DESC;
```

### 2. engagement_score

Index: `idx_trend_version_engagement` on `engagement_score DESC`

**Query Example:**
```sql
SELECT topic, engagement_score, version_date
FROM trend_version_with_details
WHERE platform = 'tiktok'
ORDER BY engagement_score DESC
LIMIT 20;
```

## Views

### trend_with_source

Convenience view joining trend with source.

```sql
SELECT * FROM trend_with_source
WHERE platform = 'tiktok'
ORDER BY first_discovered_at DESC;
```

### trend_version_with_details

Convenience view joining trend_version with trend and source.

```sql
SELECT * FROM trend_version_with_details
WHERE platform = 'tiktok'
  AND version_date = CURRENT_DATE
ORDER BY engagement_score DESC;
```

## Helper Functions

### get_or_create_trend(platform, topic, normalized_topic)

Get existing trend or create new one.

```sql
SELECT get_or_create_trend('tiktok', '#viral', 'viral');
```

### get_latest_trend_version(trend_id, version_date)

Get next version number for a trend on a date.

```sql
SELECT get_latest_trend_version(123, CURRENT_DATE);
```

## Migration

Run the migration:

```sql
-- Run in Supabase SQL Editor
\i migrations/011_create_normalized_schema.sql
```

## Usage Examples

### Insert a Trend

```sql
-- Get or create trend
SELECT get_or_create_trend('tiktok', '#viral', 'viral');

-- Or manually
INSERT INTO trend (source_id, topic, normalized_topic)
SELECT id, '#viral', 'viral'
FROM source WHERE platform = 'tiktok'
ON CONFLICT (source_id, normalized_topic) DO UPDATE
SET last_seen_at = NOW();
```

### Insert a Trend Version

```sql
-- Get trend ID
WITH trend_info AS (
    SELECT id FROM trend t
    JOIN source s ON t.source_id = s.id
    WHERE s.platform = 'tiktok' AND t.normalized_topic = 'viral'
)
INSERT INTO trend_version (
    trend_id, version_date, version_number,
    engagement_score, sentiment_polarity, sentiment_label
)
SELECT 
    id,
    CURRENT_DATE,
    get_latest_trend_version(id, CURRENT_DATE),
    8.5,
    0.75,
    'Positive'
FROM trend_info
RETURNING id;
```

### Insert Metrics

```sql
-- Insert posts metric
INSERT INTO metric (trend_version_id, metric_type, metric_value)
VALUES (123, 'posts', 1000000);

-- Insert views metric
INSERT INTO metric (trend_version_id, metric_type, metric_value)
VALUES (123, 'views', 50000000);
```

### Query Trends by Platform and Discovery Date

```sql
-- Using index: (platform, discovered_at)
SELECT 
    s.platform,
    t.topic,
    t.first_discovered_at,
    tv.engagement_score
FROM trend t
JOIN source s ON t.source_id = s.id
LEFT JOIN LATERAL (
    SELECT engagement_score
    FROM trend_version
    WHERE trend_id = t.id
    ORDER BY version_date DESC, version_number DESC
    LIMIT 1
) tv ON true
WHERE s.platform = 'tiktok'
ORDER BY t.first_discovered_at DESC
LIMIT 20;
```

### Query by Engagement Score

```sql
-- Using index: engagement_score
SELECT 
    topic,
    engagement_score,
    version_date,
    platform
FROM trend_version_with_details
WHERE engagement_score >= 7.0
ORDER BY engagement_score DESC
LIMIT 50;
```

## Comparison with Old Schema

### Old Schema (tiktok table)
- Single table with all data
- Less normalized
- Simpler queries
- Less flexible

### New Schema (normalized)
- Multiple tables with relationships
- Better normalization
- More flexible
- Better for multi-platform
- Supports versioning better

## Migration Strategy

If migrating from old schema:

1. **Run new migration** - Create normalized tables
2. **Migrate data** - Copy data from old table to new schema
3. **Update application** - Update code to use new schema
4. **Verify** - Check data integrity
5. **Deprecate old table** - Remove old table after verification

## Benefits

1. **Better Organization** - Clear separation of concerns
2. **Multi-Platform** - Easy to add new platforms
3. **Versioning** - Built-in support for daily snapshots
4. **Metrics** - Flexible metric storage
5. **Performance** - Optimized indexes for common queries
6. **Scalability** - Better for large datasets

## Related Files

- `migrations/011_create_normalized_schema.sql` - Database schema
- `NORMALIZED_SCHEMA_GUIDE.md` - This guide

---

**Status**: ✅ Normalized schema implemented
**Indexes**: (platform, discovered_at) and (engagement_score) included
**Views**: Convenience views for common queries

