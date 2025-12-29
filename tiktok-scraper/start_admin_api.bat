@echo off
REM Start admin API script for Windows

echo ==========================================
echo Starting Admin API Server
echo ==========================================

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found
    echo Make sure SUPABASE_URL and SUPABASE_KEY are set
)

REM Start admin API
python admin_api.py

