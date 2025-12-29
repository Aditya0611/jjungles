# Run History & Health Endpoint Guide

## Overview

The scraper system now includes:
1. **Health Endpoint** - Monitor worker status and job information
2. **Run History** - Persistent tracking of all scraper runs with detailed metrics

## Health Endpoint

### Worker Health Endpoint

The APScheduler worker automatically starts a health endpoint server:

```bash
# Default port: 8080
# Access at: http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "scheduler_running": true,
  "active_jobs": 2,
  "jobs": [
    {
      "id": "scraper_tiktok",
      "name": "Scraper: TikTok",
      "next_run_time": "2025-12-04T03:14:32.474095+05:30"
    },
    {
      "id": "reload_configs",
      "name": "Reload Platform Configurations",
      "next_run_time": "2025-12-04T00:19:32.475034+05:30"
    }
  ],
  "platform_configs": 1,
  "timestamp": "2025-12-04T00:14:32.476000+00:00"
}
```

### Configuration

```bash
# Set custom health port
HEALTH_PORT=9000 python worker_apscheduler.py

# Health endpoint will be at: http://localhost:9000/health
```

### Admin API Health Endpoint

The admin API also has a health endpoint:

```bash
# Admin API health
curl http://localhost:5000/health
```

## Run History

### Database Schema

Run history is stored in the `run_history` table with:
- **Start/End timestamps** - When the run started and ended
- **Duration** - Execution time in seconds
- **Record counts** - Records scraped and uploaded
- **Error information** - Error messages and tracebacks
- **Status** - running, completed, failed, cancelled
- **Metadata** - Platform configuration details

### Migration

Run the migration to create the table:

```sql
-- Run in Supabase SQL Editor
\i migrations/010_create_run_history.sql
```

### Automatic Tracking

Run history is automatically created and updated by the worker:

1. **On Start**: Creates a "running" record
2. **On Completion**: Updates with status, duration, and record counts
3. **On Error**: Updates with error message and traceback

### Query Run History

#### Via Admin API

```bash
# Get recent runs
curl http://localhost:5000/api/run-history

# Get runs for specific platform
curl http://localhost:5000/api/run-history?platform=tiktok

# Get failed runs
curl http://localhost:5000/api/run-history?status=failed

# Get runs from last 30 days
curl http://localhost:5000/api/run-history?days=30

# Get specific run
curl http://localhost:5000/api/run-history/123

# Get statistics
curl http://localhost:5000/api/run-history/stats?platform=tiktok&days=7
```

#### Via SQL

```sql
-- Get recent runs
SELECT * FROM run_history 
ORDER BY started_at DESC 
LIMIT 10;

-- Get failed runs
SELECT * FROM run_history 
WHERE status = 'failed' 
ORDER BY started_at DESC;

-- Get statistics
SELECT * FROM get_run_statistics('tiktok', 7);

-- Get average performance
SELECT 
    platform,
    AVG(duration_seconds) as avg_duration,
    AVG(records_scraped) as avg_records,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_runs
FROM run_history
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY platform;
```

## API Endpoints

### Health Endpoints

1. **Worker Health** - `GET http://localhost:8080/health`
   - Returns worker status and job information
   - No authentication required

2. **Admin API Health** - `GET http://localhost:5000/health`
   - Returns API status and Supabase connection
   - No authentication required

### Run History Endpoints

1. **Get Run History** - `GET /api/run-history`
   - Query parameters:
     - `platform` - Filter by platform
     - `status` - Filter by status (running, completed, failed, cancelled)
     - `days` - Number of days to look back (default: 7)
     - `limit` - Number of records (default: 50, max: 500)

2. **Get Run Details** - `GET /api/run-history/<run_id>`
   - Get specific run history record

3. **Get Statistics** - `GET /api/run-history/stats`
   - Query parameters:
     - `platform` - Filter by platform
     - `days` - Number of days to analyze (default: 7)
   - Returns aggregated statistics

## Example Usage

### Monitor Worker Health

```bash
# Check worker status
curl http://localhost:8080/health | jq

# Check if scheduler is running
curl http://localhost:8080/health | jq '.scheduler_running'

# Get next run times
curl http://localhost:8080/health | jq '.jobs[].next_run_time'
```

### View Run History

```bash
# Get last 10 runs
curl http://localhost:5000/api/run-history?limit=10 | jq

# Get failed runs
curl http://localhost:5000/api/run-history?status=failed | jq

# Get TikTok runs from last 24 hours
curl "http://localhost:5000/api/run-history?platform=tiktok&days=1" | jq
```

### Get Statistics

```bash
# Get overall statistics
curl http://localhost:5000/api/run-history/stats | jq

# Get TikTok statistics
curl "http://localhost:5000/api/run-history/stats?platform=tiktok&days=7" | jq
```

## Monitoring & Alerts

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8080/health"
STATUS=$(curl -s $HEALTH_URL | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
    echo "Worker is not healthy! Status: $STATUS"
    exit 1
fi

echo "Worker is healthy"
```

### Run History Monitoring

```sql
-- Check for stuck runs (running for more than 1 hour)
SELECT * FROM run_history 
WHERE status = 'running' 
  AND started_at < NOW() - INTERVAL '1 hour';

-- Check failure rate
SELECT 
    platform,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 2) as failure_rate
FROM run_history
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY platform;
```

## Integration

### With Monitoring Systems

The health endpoint can be integrated with:
- **Prometheus** - Scrape metrics from health endpoint
- **Grafana** - Visualize worker status
- **Uptime monitoring** - Check worker availability
- **Alerting systems** - Trigger alerts on failures

### With Logging Systems

Run history provides:
- **Structured data** - Easy to query and analyze
- **Error tracking** - Full error messages and tracebacks
- **Performance metrics** - Duration and record counts
- **Trend analysis** - Historical performance data

## Best Practices

1. **Monitor Health Endpoint** - Set up regular health checks
2. **Review Run History** - Check for patterns in failures
3. **Set Up Alerts** - Alert on high failure rates or stuck runs
4. **Archive Old Data** - Periodically archive old run history
5. **Analyze Performance** - Use statistics to optimize intervals

## Related Files

- `migrations/010_create_run_history.sql` - Database schema
- `worker_apscheduler.py` - Worker with health endpoint and run history
- `admin_api.py` - Admin API with run history endpoints
- `RUN_HISTORY_GUIDE.md` - This guide

---

**Status**: ✅ Health endpoint and run history implemented
**Health Port**: 8080 (configurable via HEALTH_PORT env var)
**Run History**: Automatically tracked for all scraper runs

