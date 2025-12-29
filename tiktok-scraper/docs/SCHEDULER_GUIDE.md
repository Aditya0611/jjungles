# Automated Scheduler Guide

## Overview

The automated scheduler system allows scrapers to run automatically every 2-4 hours (configurable) with admin-manageable frequency settings stored in the database.

## Features

### 1. Automated Scheduling
- Runs scrapers automatically at configurable intervals
- Default: Every 3 hours (2-4 hour range supported)
- Supports multiple platforms: TikTok, Instagram, X, LinkedIn, Facebook
- Graceful shutdown on SIGINT/SIGTERM

### 2. Admin-Configurable Frequency
- Frequency stored in database (`scheduler_settings` table)
- Can be changed without code modifications
- Range: 0.5 hours (30 min) to 24 hours
- Changes take effect on next check cycle

### 3. Platform Management
- Enable/disable platforms individually
- Track run statistics (success/failure counts)
- Automatic next-run calculation
- Platform-specific metadata (region, headless, etc.)

### 4. Admin API
- REST API for managing scheduler settings
- Update frequency, enable/disable platforms
- View statistics and run history
- CORS-enabled for admin dashboard

## Installation

### 1. Run Database Migration

```sql
-- Run migration to create scheduler_settings table
\i migrations/009_create_scheduler_settings.sql
```

This creates:
- `scheduler_settings` table
- Database functions for run statistics
- Default settings for all platforms

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies:
- `flask>=3.0.0` - Admin API server
- `flask-cors>=4.0.0` - CORS support

## Usage

### Start Scheduler

```bash
# Start scheduler (runs forever)
python scheduler.py
```

The scheduler will:
1. Load platform configurations from database
2. Check every 60 seconds for platforms that should run
3. Run enabled platforms when their `next_run_at` time arrives
4. Update run statistics after each run

### Environment Variables

```bash
# Scheduler settings
SCHEDULER_ENABLED=true              # Enable/disable scheduler (default: true)
SCHEDULER_CHECK_INTERVAL=60         # Check interval in seconds (default: 60)

# Supabase (required)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Start Admin API

```bash
# Start admin API server
python admin_api.py

# Or with custom port
ADMIN_API_PORT=8080 python admin_api.py
```

Admin API runs on:
- Default: `http://localhost:5000`
- Custom: Set `ADMIN_API_PORT` environment variable

## Admin API Endpoints

### Get All Settings

```bash
GET /api/settings

# Response
[
  {
    "id": 1,
    "platform": "tiktok",
    "enabled": true,
    "frequency_hours": 3.0,
    "last_run_at": "2024-01-15T10:00:00Z",
    "next_run_at": "2024-01-15T13:00:00Z",
    "run_count": 10,
    "success_count": 9,
    "failure_count": 1,
    "metadata": {"region": "en", "headless": true}
  },
  ...
]
```

### Get Platform Settings

```bash
GET /api/settings/tiktok

# Response
{
  "id": 1,
  "platform": "tiktok",
  "enabled": true,
  "frequency_hours": 3.0,
  ...
}
```

### Update Platform Settings

```bash
PUT /api/settings/tiktok
Content-Type: application/json

{
  "enabled": true,
  "frequency_hours": 2.5,
  "metadata": {"region": "en", "headless": true}
}
```

### Update Frequency Only

```bash
PUT /api/settings/tiktok/frequency
Content-Type: application/json

{
  "frequency_hours": 2.0
}
```

### Enable Platform

```bash
POST /api/settings/tiktok/enable
```

### Disable Platform

```bash
POST /api/settings/tiktok/disable
```

### Get Statistics

```bash
GET /api/stats

# Response
{
  "total_platforms": 5,
  "enabled_platforms": 2,
  "total_runs": 50,
  "total_successes": 48,
  "total_failures": 2,
  "platforms": [...]
}
```

### Health Check

```bash
GET /health

# Response
{
  "status": "healthy",
  "supabase_available": true,
  "timestamp": "2024-01-15T10:00:00Z"
}
```

## Database Management

### Update Frequency via SQL

```sql
-- Update TikTok to run every 2 hours
UPDATE public.scheduler_settings 
SET frequency_hours = 2.0 
WHERE platform = 'tiktok';

-- Update Instagram to run every 4 hours
UPDATE public.scheduler_settings 
SET frequency_hours = 4.0 
WHERE platform = 'instagram';
```

### Enable/Disable Platforms

```sql
-- Enable TikTok
UPDATE public.scheduler_settings 
SET enabled = true 
WHERE platform = 'tiktok';

-- Disable Instagram
UPDATE public.scheduler_settings 
SET enabled = false 
WHERE platform = 'instagram';
```

### View Settings

```sql
-- Get all settings
SELECT * FROM public.scheduler_settings ORDER BY platform;

-- Get next platform to run
SELECT * FROM get_next_platform_to_run();

-- Get enabled platforms
SELECT platform, frequency_hours, next_run_at 
FROM public.scheduler_settings 
WHERE enabled = true 
ORDER BY next_run_at ASC;
```

## Example: Change Frequency

### Via Admin API

```bash
# Change TikTok frequency to 2 hours
curl -X PUT http://localhost:5000/api/settings/tiktok/frequency \
  -H "Content-Type: application/json" \
  -d '{"frequency_hours": 2.0}'

# Change Instagram frequency to 4 hours
curl -X PUT http://localhost:5000/api/settings/instagram/frequency \
  -H "Content-Type: application/json" \
  -d '{"frequency_hours": 4.0}'
```

### Via SQL

```sql
-- Update multiple platforms
UPDATE public.scheduler_settings 
SET frequency_hours = 2.0 
WHERE platform = 'tiktok';

UPDATE public.scheduler_settings 
SET frequency_hours = 4.0 
WHERE platform = 'instagram';
```

## Platform Configuration

### Default Settings

All platforms are created with default settings:

- **TikTok**: Enabled, 3 hours
- **Instagram**: Disabled, 3 hours
- **X**: Disabled, 3 hours
- **LinkedIn**: Disabled, 3 hours
- **Facebook**: Disabled, 3 hours

### Metadata

Each platform can have custom metadata:

```json
{
  "region": "en",
  "headless": true,
  "upload_to_db": true
}
```

This metadata is passed to the scraper when it runs.

## Monitoring

### Scheduler Logs

The scheduler logs:
- Platform configurations loaded
- Platforms scheduled to run
- Scraper start/completion
- Run statistics updates
- Errors and warnings

### Database Statistics

Track performance via database:

```sql
-- Get run statistics
SELECT 
    platform,
    enabled,
    frequency_hours,
    run_count,
    success_count,
    failure_count,
    ROUND(100.0 * success_count / NULLIF(run_count, 0), 2) as success_rate,
    last_run_at,
    next_run_at
FROM public.scheduler_settings
ORDER BY platform;
```

### Admin API Stats

```bash
# Get statistics
curl http://localhost:5000/api/stats
```

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/scraper-scheduler.service`:

```ini
[Unit]
Description=TikTok Scraper Scheduler
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/scraper
Environment="SUPABASE_URL=your_url"
Environment="SUPABASE_KEY=your_key"
Environment="SCHEDULER_ENABLED=true"
ExecStart=/usr/bin/python3 /path/to/scraper/scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl enable scraper-scheduler
sudo systemctl start scraper-scheduler
sudo systemctl status scraper-scheduler
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "scheduler.py"]
```

Run:

```bash
docker build -t scraper-scheduler .
docker run -d \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_KEY=your_key \
  -e SCHEDULER_ENABLED=true \
  --name scraper-scheduler \
  scraper-scheduler
```

## Troubleshooting

### Scheduler Not Running

1. Check if enabled:
   ```bash
   echo $SCHEDULER_ENABLED  # Should be "true"
   ```

2. Check Supabase connection:
   ```bash
   python -c "from scheduler import Scheduler; s = Scheduler(); print(s.supabase)"
   ```

3. Check logs for errors

### Platform Not Running

1. Check if enabled in database:
   ```sql
   SELECT enabled FROM scheduler_settings WHERE platform = 'tiktok';
   ```

2. Check next_run_at:
   ```sql
   SELECT next_run_at FROM scheduler_settings WHERE platform = 'tiktok';
   ```

3. Check if already running (scheduler won't start duplicate)

### Frequency Not Updating

- Changes take effect on next check cycle (default: 60 seconds)
- Verify update in database:
  ```sql
  SELECT frequency_hours FROM scheduler_settings WHERE platform = 'tiktok';
  ```

## Related Files

- `scheduler.py` - Main scheduler implementation
- `admin_api.py` - Admin API for managing settings
- `migrations/009_create_scheduler_settings.sql` - Database schema
- `base.py` - Scraper implementation

---

**Status**: ✅ Implemented
**Default Frequency**: 3 hours (configurable 0.5-24 hours)
**Platforms**: TikTok, Instagram, X, LinkedIn, Facebook

