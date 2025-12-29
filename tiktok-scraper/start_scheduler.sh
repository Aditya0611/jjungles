#!/bin/bash
# Start scheduler script

echo "=========================================="
echo "Starting Scraper Scheduler"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "Make sure SUPABASE_URL and SUPABASE_KEY are set"
fi

# Start scheduler
python scheduler.py

