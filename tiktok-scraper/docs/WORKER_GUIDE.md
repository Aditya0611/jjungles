# Worker & Job Scheduling Guide

## Overview

This guide covers different options for running scraper jobs automatically:
1. **APScheduler** - Lightweight, in-process scheduler (recommended for single-server)
2. **Celery** - Distributed task queue (recommended for multi-server)
3. **RQ** - Simple Redis queue (lightweight alternative)
4. **Cron** - System-level scheduling (simple but limited)

## Comparison

| Feature | APScheduler | Celery | RQ | Cron |
|---------|-------------|--------|----|----|
| **Complexity** | Low | Medium | Low | Very Low |
| **Dependencies** | None | Redis/RabbitMQ | Redis | None |
| **Distributed** | No | Yes | Yes | No |
| **Dynamic Jobs** | Yes | Yes | Yes | No |
| **Monitoring** | Basic | Flower | RQ Dashboard | None |
| **Best For** | Single server | Multi-server | Simple queue | Simple needs |

## 1. APScheduler Worker (Recommended)

### Features
- ✅ No external dependencies (no Redis/RabbitMQ)
- ✅ Dynamic job management
- ✅ Async support
- ✅ Automatic config reload
- ✅ Job persistence (optional)

### Installation

```bash
pip install apscheduler
```

### Usage

```bash
# Start worker
python worker_apscheduler.py
```

### Configuration

```bash
# Environment variables
WORKER_ENABLED=true                    # Enable/disable worker
WORKER_RELOAD_INTERVAL=300             # Reload configs every 5 minutes
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### How It Works

1. Loads platform configurations from `scheduler_settings` table
2. Creates interval-based jobs (every N hours)
3. Automatically reloads configurations every 5 minutes
4. Runs scrapers as async tasks
5. Updates run statistics in database

### Job Management

Jobs are automatically created/updated based on database settings:
- Enable/disable platforms → Jobs added/removed
- Change frequency → Jobs rescheduled
- No code changes needed

## 2. Celery Worker (Distributed)

### Features
- ✅ Distributed/scaled deployments
- ✅ Multiple worker processes
- ✅ Task persistence
- ✅ Monitoring with Flower
- ✅ Task retries and error handling

### Installation

```bash
pip install celery redis
```

### Setup Redis

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Install Redis (macOS)
brew install redis

# Start Redis
redis-server
```

### Usage

```bash
# Terminal 1: Start worker
celery -A worker_celery worker --loglevel=info

# Terminal 2: Start beat scheduler
celery -A worker_celery beat --loglevel=info

# Or use wrapper
python worker_celery.py worker
python worker_celery.py beat
```

### Configuration

```bash
# Environment variables
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Monitoring with Flower

```bash
# Install Flower
pip install flower

# Start Flower
celery -A worker_celery flower

# Access at http://localhost:5555
```

### Scaling

Run multiple workers:

```bash
# Worker 1
celery -A worker_celery worker --loglevel=info --hostname=worker1@%h

# Worker 2
celery -A worker_celery worker --loglevel=info --hostname=worker2@%h
```

## 3. RQ Worker (Simple Queue)

### Features
- ✅ Simple Redis-based queue
- ✅ Lightweight
- ✅ Easy to use
- ✅ Good for single-worker setups

### Installation

```bash
pip install rq rq-scheduler
```

### Setup Redis

Same as Celery (see above).

### Usage

```bash
# Terminal 1: Start worker
python worker_rq.py worker

# Terminal 2: Start scheduler
python worker_rq.py scheduler
```

### Configuration

```bash
# Environment variables
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Monitoring

```bash
# Install RQ Dashboard
pip install rq-dashboard

# Start dashboard
rq-dashboard

# Access at http://localhost:9181
```

## 4. Cron (System-Level)

### Features
- ✅ No Python dependencies
- ✅ System-native
- ✅ Simple setup
- ❌ No dynamic job management
- ❌ Limited monitoring

### Setup

```bash
# Make script executable
chmod +x cron_setup.sh

# Run setup
./cron_setup.sh
```

### Manual Cron Setup

```bash
# Edit crontab
crontab -e

# Add job (every 3 hours)
0 */3 * * * cd /path/to/scraper && /usr/bin/python3 base.py >> /var/log/scraper.log 2>&1
```

### Cron Schedule Examples

```bash
# Every 2 hours
0 */2 * * * ...

# Every 4 hours
0 */4 * * * ...

# Every day at 2 AM
0 2 * * * ...

# Every 30 minutes
*/30 * * * * ...
```

## Production Deployment

### APScheduler (Single Server)

```bash
# systemd service
sudo nano /etc/systemd/system/scraper-worker.service
```

```ini
[Unit]
Description=Scraper APScheduler Worker
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/scraper
Environment="SUPABASE_URL=your_url"
Environment="SUPABASE_KEY=your_key"
ExecStart=/usr/bin/python3 /path/to/scraper/worker_apscheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable scraper-worker
sudo systemctl start scraper-worker
```

### Celery (Distributed)

```bash
# systemd service for worker
sudo nano /etc/systemd/system/celery-worker.service
```

```ini
[Unit]
Description=Celery Scraper Worker
After=network.target redis.target

[Service]
Type=forking
User=your-user
WorkingDirectory=/path/to/scraper
Environment="REDIS_URL=redis://localhost:6379/0"
ExecStart=/usr/bin/celery -A worker_celery worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# systemd service for beat
sudo nano /etc/systemd/system/celery-beat.service
```

```ini
[Unit]
Description=Celery Beat Scheduler
After=network.target redis.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/scraper
Environment="REDIS_URL=redis://localhost:6379/0"
ExecStart=/usr/bin/celery -A worker_celery beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring

### APScheduler

```python
# Check active jobs
from worker_apscheduler import APSchedulerWorker
worker = APSchedulerWorker()
for job in worker.scheduler.get_jobs():
    print(f"{job.name}: Next run at {job.next_run_time}")
```

### Celery

```bash
# Check worker status
celery -A worker_celery inspect active

# Check scheduled tasks
celery -A worker_celery inspect scheduled
```

### RQ

```bash
# Check queue status
rq info

# Check worker status
rq worker --url redis://localhost:6379/0
```

## Troubleshooting

### APScheduler: Jobs not running

- Check if worker is running: `ps aux | grep worker_apscheduler`
- Check logs for errors
- Verify database connection
- Check if platforms are enabled in database

### Celery: Tasks stuck

- Check Redis connection: `redis-cli ping`
- Check worker logs
- Restart workers: `celery -A worker_celery control shutdown`

### RQ: Jobs not scheduled

- Check Redis connection
- Verify scheduler is running
- Check scheduler logs

### Cron: Jobs not executing

- Check cron logs: `grep CRON /var/log/syslog`
- Verify Python path: `which python3`
- Check file permissions
- Verify environment variables

## Recommendation

**For most users**: Use **APScheduler** (`worker_apscheduler.py`)
- No external dependencies
- Easy to set up
- Dynamic job management
- Good for single-server deployments

**For distributed setups**: Use **Celery** (`worker_celery.py`)
- Multiple workers
- Task persistence
- Better monitoring
- Production-ready

**For simple needs**: Use **Cron**
- No Python dependencies
- System-native
- Simple setup

---

**Status**: ✅ All worker options implemented
**Default**: APScheduler (recommended)

