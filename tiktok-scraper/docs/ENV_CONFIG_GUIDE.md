# Environment Configuration Guide

## Overview

The scraper system supports environment variable configuration and runtime overrides for scrape intervals and other settings.

## Environment Variables

### Scrape Interval Configuration

```bash
# Default scrape interval (hours)
SCRAPE_INTERVAL_HOURS=3.0          # Default: 3.0 hours (2-4 hour range)

# Interval limits
SCRAPE_INTERVAL_MIN=0.5            # Minimum: 0.5 hours (30 minutes)
SCRAPE_INTERVAL_MAX=24.0           # Maximum: 24.0 hours
```

### Worker Configuration

```bash
# Worker settings
WORKER_ENABLED=true                # Enable/disable worker
WORKER_RELOAD_INTERVAL=300         # Reload configs every 5 minutes (seconds)
```

### Scheduler Configuration

```bash
# Scheduler settings
SCHEDULER_ENABLED=true             # Enable/disable scheduler
SCHEDULER_CHECK_INTERVAL=60        # Check interval (seconds)
```

### Database Configuration

```bash
# Supabase (required)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Proxy Configuration

```bash
# Proxy settings (optional)
PROXY_SERVER=http://proxy.example.com:8080
PROXY_USERNAME=username
PROXY_PASSWORD=password
PROXY_LIST=proxy1:port,proxy2:port
```

### Logging Configuration

```bash
# Logging
USE_JSON_LOGGING=false            # Use JSON logging (default: false)
```

## Configuration Priority

Settings are applied in this order (highest to lowest priority):

1. **Runtime Override** (command-line arguments)
2. **Environment Variables** (`.env` file or system env)
3. **Database Settings** (`scheduler_settings` table)
4. **Default Values** (hardcoded defaults)

## Usage Examples

### 1. Environment Variable Configuration

Create a `.env` file:

```bash
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
SCRAPE_INTERVAL_HOURS=2.5
WORKER_ENABLED=true
```

Then run:

```bash
python worker_apscheduler.py
```

### 2. Runtime Override (Command-Line)

```bash
# Override interval to 2 hours
python worker_apscheduler.py --interval 2.0

# Override interval to 4 hours
python worker_apscheduler.py --interval 4.0

# Override with custom min/max
python worker_apscheduler.py --interval 1.5 --min-interval 0.5 --max-interval 12.0
```

### 3. System Environment Variables

```bash
# Set in shell
export SCRAPE_INTERVAL_HOURS=2.0
export WORKER_ENABLED=true

# Run worker
python worker_apscheduler.py
```

### 4. Docker Environment

```dockerfile
# Dockerfile
ENV SCRAPE_INTERVAL_HOURS=3.0
ENV WORKER_ENABLED=true
ENV SUPABASE_URL=your_url
ENV SUPABASE_KEY=your_key
```

```bash
# Or via docker run
docker run -e SCRAPE_INTERVAL_HOURS=2.0 -e SUPABASE_URL=... scraper
```

## Worker-Specific Configuration

### APScheduler Worker

```bash
# Environment variables
SCRAPE_INTERVAL_HOURS=3.0
WORKER_ENABLED=true
WORKER_RELOAD_INTERVAL=300

# Runtime override
python worker_apscheduler.py --interval 2.5
```

### Celery Worker

```bash
# Environment variables
SCRAPE_INTERVAL_HOURS=3.0
REDIS_URL=redis://localhost:6379/0

# Note: Celery uses database settings primarily
# Env vars are used as fallback
```

### RQ Worker

```bash
# Environment variables
SCRAPE_INTERVAL_HOURS=3.0
REDIS_URL=redis://localhost:6379/0
```

### Simple Scheduler

```bash
# Environment variables
SCRAPE_INTERVAL_HOURS=3.0
SCHEDULER_ENABLED=true
SCHEDULER_CHECK_INTERVAL=60

# Runtime override
python scheduler.py --interval 2.5
```

## Configuration Examples

### Example 1: High-Frequency Scraping (Every 2 Hours)

```bash
# .env
SCRAPE_INTERVAL_HOURS=2.0

# Run
python worker_apscheduler.py
```

### Example 2: Low-Frequency Scraping (Every 6 Hours)

```bash
# .env
SCRAPE_INTERVAL_HOURS=6.0

# Run
python worker_apscheduler.py
```

### Example 3: Runtime Override for Testing

```bash
# Test with 30-minute interval
python worker_apscheduler.py --interval 0.5
```

### Example 4: Production with Custom Limits

```bash
# .env
SCRAPE_INTERVAL_HOURS=3.0
SCRAPE_INTERVAL_MIN=1.0    # Minimum 1 hour
SCRAPE_INTERVAL_MAX=12.0   # Maximum 12 hours

# Run
python worker_apscheduler.py
```

## Integration with Database Settings

When database settings are available:

1. **Database settings take precedence** over env vars
2. **Env vars are used as fallback** if database is unavailable
3. **Runtime overrides** apply to default configs only (not database values)

Example:

```bash
# Database has: TikTok = 3.0 hours
# Env var: SCRAPE_INTERVAL_HOURS=2.0
# Runtime: --interval 1.5

# Result: TikTok uses 3.0 hours (from database)
#         Other platforms use 2.0 hours (from env)
#         Runtime override only affects defaults if database unavailable
```

## Validation

Intervals are automatically validated:

- **Minimum**: 0.5 hours (30 minutes)
- **Maximum**: 24.0 hours
- **Default**: 3.0 hours

Invalid values are clamped to valid range with a warning.

## Troubleshooting

### Issue: Interval not applying

**Solution**: Check configuration priority:
1. Database settings (if table exists)
2. Environment variables
3. Runtime overrides
4. Defaults

### Issue: Interval out of range

**Solution**: Check min/max limits:
```bash
# Set custom limits
export SCRAPE_INTERVAL_MIN=1.0
export SCRAPE_INTERVAL_MAX=12.0
```

### Issue: Database settings override env vars

**Solution**: This is expected behavior. Database settings take precedence. To use env vars:
1. Disable platform in database, OR
2. Update database settings to match env vars

## Best Practices

1. **Use `.env` file** for local development
2. **Use system env vars** for production
3. **Use database settings** for dynamic configuration
4. **Use runtime overrides** for testing/debugging
5. **Set appropriate limits** (min/max) for production

## Related Files

- `worker_apscheduler.py` - APScheduler worker with env/runtime support
- `scheduler.py` - Simple scheduler with env/runtime support
- `.env` - Environment variable file (create this)
- `ENV_CONFIG_GUIDE.md` - This guide

---

**Status**: ✅ Environment configuration implemented
**Priority**: Runtime Override > Env Vars > Database > Defaults

