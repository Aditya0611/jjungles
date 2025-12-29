#!/bin/bash
# Smoke test script to verify scraper functionality and DB insertion
echo "Starting Smoke Test..."

# 1. Run a quick scrape (requires ENV vars to be set)
echo "Running Scraper (limit 1 for speed)..."
python base.py --platform TikTok --limit 1 --no-headless

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Scraper finished successfully."
    
    # 2. (Optional) Python script to verify DB count if needed
    # python check_db_count.py
    
else
    echo "Scraper failed with exit code $exit_code"
    exit 1
fi
