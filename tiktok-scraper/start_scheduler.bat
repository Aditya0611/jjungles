@echo off
REM Start scheduler script for Windows

echo ==========================================
echo Starting Scraper Scheduler
echo ==========================================

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found
    echo Make sure SUPABASE_URL and SUPABASE_KEY are set
)

REM Start scheduler
python scheduler.py

