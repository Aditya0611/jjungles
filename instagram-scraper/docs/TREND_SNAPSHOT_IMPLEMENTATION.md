# Daily Snapshot/Versioning Implementation

## ✅ Implementation Complete

Daily snapshot and versioning system has been fully implemented to track trend changes over time.

## What Was Implemented

### 1. Trend Snapshot Module (`trend_snapshot.py`) ✅

**Features:**
- **Daily Snapshots**: Creates snapshots of trends normalized to midnight (daily)
- **Version Tracking**: Links snapshots to scraper run version IDs
- **Change Comparison**: Automatically compares with previous snapshots
- **Rank Tracking**: Tracks trend rank among all trends on each date
- **Historical Analysis**: Query trends by date, compare across time periods
- **Trend History**: Get trend history for last N days
- **Significant Changes**: Identify trends with significant changes

**Key Classes:**
- `TrendSnapshot`: Data class for snapshot data
- `TrendSnapshotManager`: Manages snapshot creation, storage, and queries

### 2. Integration into Main Scraper (`main.py`) ✅

**Integration Points:**
1. **Snapshot Manager Initialization**: Created in `save_trends_to_database()`
2. **Snapshot Creation**: After bulk insert, creates snapshots for all trends
3. **Rank Assignment**: Ranks trends by engagement score
4. **Change Detection**: Automatically detects and logs significant changes
5. **Console Output**: Displays snapshot creation status

## How It Works

### 1. Snapshot Creation

**Process:**
1. After trends are saved to database
2. Trends are sorted by engagement score
3. Ranks are assigned (1 = highest engagement)
4. For each trend:
   - Create snapshot with current data
   - Compare with previous snapshot (if exists)
   - Calculate changes (percent change, direction)
   - Save snapshot to database

**Snapshot Data:**
- Trend identifier (hashtag)
- Snapshot date (normalized to midnight)
- Version ID (scraper run ID)
- Engagement metrics (score, likes, comments, views, shares)
- Rank among trends
- Change from previous snapshot
- Metadata (category, content types, language, etc.)

### 2. Change Comparison

**Automatic Comparison:**
- Compares with latest snapshot before current date
- Calculates:
  - Absolute change (current - previous)
  - Percent change ((current - previous) / previous × 100)
  - Direction (up, down, stable)
- Tracks changes for:
  - Engagement score
  - Likes
  - Comments
  - Views
  - Rank

**Example:**
```python
{
    'engagement_score': {
        'previous': 1000.0,
        'current': 1500.0,
        'absolute_change': 500.0,
        'percent_change': 50.0,
        'direction': 'up'
    },
    'rank': {
        'previous': 5,
        'current': 2,
        'absolute_change': 3,  # Moved up 3 positions
        'direction': 'up'
    }
}
```

### 3. Database Schema

**Table: `trend_snapshots`**

```sql
CREATE TABLE trend_snapshots (
    id SERIAL PRIMARY KEY,
    trend_id TEXT NOT NULL,  -- Hashtag identifier
    snapshot_date DATE NOT NULL,  -- Date of snapshot (normalized to midnight)
    version_id TEXT NOT NULL,  -- Scraper run version ID
    platform TEXT NOT NULL,
    hashtag TEXT NOT NULL,
    engagement_score FLOAT NOT NULL,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    language TEXT,
    sentiment_polarity FLOAT,
    sentiment_label TEXT,
    posts_count INTEGER DEFAULT 0,
    rank INTEGER,  -- Rank among trends on this date
    change_from_previous JSONB,  -- Comparison with previous snapshot
    metadata JSONB,  -- Additional metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trend_id, snapshot_date)  -- One snapshot per trend per day
);

-- Indexes for fast queries
CREATE INDEX idx_trend_snapshots_trend_id ON trend_snapshots(trend_id);
CREATE INDEX idx_trend_snapshots_date ON trend_snapshots(snapshot_date);
CREATE INDEX idx_trend_snapshots_platform_date ON trend_snapshots(platform, snapshot_date);
CREATE INDEX idx_trend_snapshots_version ON trend_snapshots(version_id);
```

## Usage Examples

### Get Trend History

```python
from trend_snapshot import TrendSnapshotManager
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
manager = TrendSnapshotManager(supabase)

# Get last 30 days of history for a trend
history = manager.get_trend_history('trending', days=30)

for snapshot in history:
    print(f"Date: {snapshot['snapshot_date']}")
    print(f"Engagement: {snapshot['engagement_score']}")
    print(f"Rank: {snapshot['rank']}")
    if snapshot.get('change_from_previous'):
        change = snapshot['change_from_previous']['engagement_score']
        print(f"Change: {change['percent_change']:+.1f}%")
```

### Compare Trends Between Dates

```python
from datetime import datetime, timedelta

today = datetime.utcnow()
yesterday = today - timedelta(days=1)

comparison = manager.compare_trends('trending', yesterday, today)

if comparison:
    print(f"Engagement Change: {comparison['changes']['engagement_score']['percent_change']:+.1f}%")
    print(f"Rank Change: {comparison['changes']['rank']['absolute_change']}")
```

### Get Trends for Specific Date

```python
date = datetime(2024, 1, 15)
trends = manager.get_trends_by_date(date, platform='Instagram', limit=10)

for trend in trends:
    print(f"#{trend['hashtag']}: Rank {trend['rank']}, Score {trend['engagement_score']}")
```

### Find Significant Changes

```python
# Get trends with >10% change in last 7 days
significant_changes = manager.get_trending_changes(days=7, min_change_percent=10.0)

for change in significant_changes:
    hashtag = change['hashtag']
    percent_change = change['changes']['engagement_score']['percent_change']
    direction = change['changes']['engagement_score']['direction']
    print(f"#{hashtag}: {direction} {percent_change:+.1f}%")
```

## Integration Details

### In `save_trends_to_database()`

**After Bulk Insert:**
1. Sort all trends by engagement score
2. Assign ranks (1 = highest)
3. Create snapshot for each trend
4. Compare with previous snapshot
5. Save snapshots to database
6. Log significant changes (>5%)

**Console Output:**
```
📸 Creating daily snapshots for versioning...
   ✅ Created 10 daily snapshots
```

**Logging:**
- Logs trends with significant changes (>5%)
- Includes percent change and direction
- Includes rank information

## Benefits

1. **Historical Tracking**: See how trends change over time
2. **Trend Analysis**: Identify rising/falling trends
3. **Rank Tracking**: See how trends move in rankings
4. **Change Detection**: Automatically detect significant changes
5. **Time-Series Data**: Enable time-series analysis and visualization
6. **Version Control**: Link snapshots to scraper run versions
7. **Comparison**: Easy comparison between any two dates

## Query Examples

### Get Rising Trends (Last 7 Days)

```python
changes = manager.get_trending_changes(days=7, min_change_percent=20.0)
rising = [c for c in changes if c['changes']['engagement_score']['direction'] == 'up']
```

### Get Top Trends for Date

```python
date = datetime(2024, 1, 15)
top_trends = manager.get_trends_by_date(date, limit=10, order_by='engagement_score')
```

### Get Trend Trajectory

```python
history = manager.get_trend_history('trending', days=30)
trajectory = [s['engagement_score'] for s in history]
# Plot trajectory to see trend over time
```

## Data Structure

### Snapshot Structure

```python
{
    'trend_id': 'trending',
    'snapshot_date': '2024-01-15T00:00:00',
    'version_id': 'v1.0.0-20240115-123456',
    'platform': 'Instagram',
    'hashtag': '#trending',
    'engagement_score': 3660.0,
    'likes': 1000,
    'comments': 50,
    'views': 50000,
    'shares': 0,
    'language': 'en',
    'sentiment_polarity': 0.15,
    'sentiment_label': 'positive',
    'posts_count': 10,
    'rank': 1,
    'change_from_previous': {
        'engagement_score': {
            'previous': 3000.0,
            'current': 3660.0,
            'absolute_change': 660.0,
            'percent_change': 22.0,
            'direction': 'up'
        },
        'rank': {
            'previous': 3,
            'current': 1,
            'absolute_change': 2,
            'direction': 'up'
        }
    },
    'metadata': {
        'category': 'fashion',
        'content_types': {'photo': 2, 'reel': 1},
        'primary_format': 'photo'
    }
}
```

## Files Created/Modified

1. ✅ `trend_snapshot.py` - Snapshot manager module (500+ lines)
2. ✅ `main.py` - Integrated snapshot creation
3. ✅ `TREND_SNAPSHOT_IMPLEMENTATION.md` - This documentation

## Database Setup

**Create the snapshot table:**

```sql
CREATE TABLE trend_snapshots (
    id SERIAL PRIMARY KEY,
    trend_id TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    version_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'Instagram',
    hashtag TEXT NOT NULL,
    engagement_score FLOAT NOT NULL,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    language TEXT,
    sentiment_polarity FLOAT,
    sentiment_label TEXT,
    posts_count INTEGER DEFAULT 0,
    rank INTEGER,
    change_from_previous JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trend_id, snapshot_date)
);

CREATE INDEX idx_trend_snapshots_trend_id ON trend_snapshots(trend_id);
CREATE INDEX idx_trend_snapshots_date ON trend_snapshots(snapshot_date);
CREATE INDEX idx_trend_snapshots_platform_date ON trend_snapshots(platform, snapshot_date);
```

## Verification

✅ Module imports successfully
✅ Snapshot manager initialized
✅ Integration complete
✅ No linting errors
✅ Ready to use

**Status: ✅ COMPLETE AND READY TO USE**

