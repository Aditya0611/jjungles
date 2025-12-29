#!/bin/bash
# Start worker script

echo "=========================================="
echo "Starting Scraper Worker"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "Make sure SUPABASE_URL and SUPABASE_KEY are set"
fi

# Choose worker type (default: APScheduler)
WORKER_TYPE=${1:-apscheduler}

case $WORKER_TYPE in
    apscheduler)
        echo "Starting APScheduler worker..."
        python worker_apscheduler.py
        ;;
    celery-worker)
        echo "Starting Celery worker..."
        celery -A worker_celery worker --loglevel=info
        ;;
    celery-beat)
        echo "Starting Celery beat scheduler..."
        celery -A worker_celery beat --loglevel=info
        ;;
    rq-worker)
        echo "Starting RQ worker..."
        python worker_rq.py worker
        ;;
    rq-scheduler)
        echo "Starting RQ scheduler..."
        python worker_rq.py scheduler
        ;;
    *)
        echo "Unknown worker type: $WORKER_TYPE"
        echo "Available types: apscheduler, celery-worker, celery-beat, rq-worker, rq-scheduler"
        exit 1
        ;;
esac

