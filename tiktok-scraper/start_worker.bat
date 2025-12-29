@echo off
REM Start worker script for Windows

echo ==========================================
echo Starting Scraper Worker
echo ==========================================

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found
    echo Make sure SUPABASE_URL and SUPABASE_KEY are set
)

REM Choose worker type (default: APScheduler)
set WORKER_TYPE=%1
if "%WORKER_TYPE%"=="" set WORKER_TYPE=apscheduler

if "%WORKER_TYPE%"=="apscheduler" (
    echo Starting APScheduler worker...
    python worker_apscheduler.py
) else if "%WORKER_TYPE%"=="rq-worker" (
    echo Starting RQ worker...
    python worker_rq.py worker
) else if "%WORKER_TYPE%"=="rq-scheduler" (
    echo Starting RQ scheduler...
    python worker_rq.py scheduler
) else (
    echo Unknown worker type: %WORKER_TYPE%
    echo Available types: apscheduler, rq-worker, rq-scheduler
    exit /b 1
)

