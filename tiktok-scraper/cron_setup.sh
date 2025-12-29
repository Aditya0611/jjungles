#!/bin/bash
# Cron setup script for scraper jobs

echo "=========================================="
echo "Cron Setup for Scraper Jobs"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

# Create cron job for TikTok (every 3 hours)
CRON_JOB="0 */3 * * * cd $SCRIPT_DIR && $PYTHON_PATH base.py >> /var/log/scraper_tiktok.log 2>&1"

echo "Cron job to add:"
echo "$CRON_JOB"
echo ""

# Ask for confirmation
read -p "Add this cron job? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job added successfully!"
    echo ""
    echo "Current crontab:"
    crontab -l
else
    echo "Cancelled."
fi

