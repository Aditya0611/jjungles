# Trend Lifecycle Management

## Overview

The scraper now includes automatic trend lifecycle management to prevent database bloat and keep only relevant trends. This system automatically expires, archives, and decays old trends.

## Features

### 1. **Trend Expiration**
- Trends older than `TREND_EXPIRATION_DAYS` (default: 30 days) are automatically handled
- Can be archived (marked as archived) or deleted based on configuration

### 2. **Trend Decay**
- Trends inactive for `TREND_INACTIVE_DAYS` (default: 14 days) have their engagement scores decayed
- Exponential decay: `score * (1 - decay_rate) ^ weeks_inactive`
- Prevents old trends from ranking high in searches
- Minimum score: 10% of original (prevents complete zero)

### 3. **Lifecycle Tracking**
- `first_seen`: When trend was first discovered
- `last_seen`: When trend was last seen/updated
- `scraped_at`: Last scrape timestamp
- `lifecycle_status`: active, inactive, or archived

## Configuration

### Environment Variables

```bash
# Trend expiration (days since last seen)
TREND_EXPIRATION_DAYS=30  # Archive/delete trends older than 30 days

# Trend inactivity threshold (days since last seen)
TREND_INACTIVE_DAYS=14  # Apply decay to trends inactive for 14+ days

# Enable/disable decay
TREND_DECAY_ENABLED=true  # Apply engagement score decay

# Decay rate per week (0.05 = 5% per week)
TREND_DECAY_RATE=0.05

# Enable/disable archiving (if false, deletes expired trends)
TREND_ARCHIVE_ENABLED=true  # Archive instead of delete
```

### Default Values

- **Expiration**: 30 days
- **Inactivity**: 14 days
- **Decay Rate**: 5% per week
- **Archive Enabled**: true (archives instead of deleting)

## How It Works

### Lifecycle States

1. **Active** (< 14 days since last seen)
   - No action taken
   - Full engagement score maintained

2. **Inactive** (14-30 days since last seen)
   - Engagement score decayed
   - Status marked as "inactive" in metadata
   - Still visible but ranked lower

3. **Expired** (> 30 days since last seen)
   - Archived (if `TREND_ARCHIVE_ENABLED=true`)
   - Deleted (if `TREND_ARCHIVE_ENABLED=false`)
   - Status marked as "archived" in metadata

### Decay Calculation

```
weeks_inactive = days_inactive / 7
decayed_score = original_score * (1 - decay_rate) ^ weeks_inactive
min_score = original_score * 0.1  # Never goes below 10%
final_score = max(decayed_score, min_score)
```

**Example:**
- Original score: 10,000
- 3 weeks inactive
- Decay rate: 5% per week
- Decayed score: 10,000 * (0.95)^3 = 8,573.75

## Automatic Cleanup

The cleanup runs automatically:
- **After each scraper run** - Cleans up old trends after saving new ones
- **Integrated into workflow** - No manual intervention needed

## Manual Cleanup

You can also run cleanup manually:

```python
from main import cleanup_old_trends, create_client, Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
results = cleanup_old_trends(supabase)
print(results)
```

## Database Schema Updates

The lifecycle system uses existing metadata fields:

```json
{
  "metadata": {
    "raw_blob": {
      "first_seen": "2025-11-01T00:00:00",
      "last_seen": "2025-11-22T00:00:00"
    },
    "lifecycle_status": "active|inactive|archived",
    "decayed_score": 8573.75,
    "decay_applied_at": "2025-11-22T00:00:00",
    "days_inactive": 21,
    "archived_at": "2025-11-30T00:00:00",
    "archived_reason": "Expired: 31 days since last seen"
  }
}
```

## Benefits

1. **Prevents Database Bloat**
   - Old trends are automatically archived/deleted
   - Keeps database size manageable

2. **Maintains Relevance**
   - Only current trends rank high
   - Old trends decay over time

3. **Lifecycle Tracking**
   - Full history of when trends were discovered
   - Track trend longevity

4. **Configurable**
   - Adjust expiration and decay rates
   - Choose archive vs delete

## Querying Archived Trends

To query only active trends:

```sql
SELECT * FROM instagram
WHERE metadata->>'lifecycle_status' IS NULL
   OR metadata->>'lifecycle_status' != 'archived'
ORDER BY scraped_at DESC;
```

To query archived trends:

```sql
SELECT * FROM instagram
WHERE metadata->>'lifecycle_status' = 'archived'
ORDER BY metadata->>'archived_at' DESC;
```

## Monitoring

The cleanup process logs:
- Number of expired trends found
- Number archived/deleted
- Number decayed
- Any errors encountered

Check logs for cleanup summaries after each scraper run.

