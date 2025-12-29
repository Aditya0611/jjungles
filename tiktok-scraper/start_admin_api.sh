#!/bin/bash
# Start admin API script

echo "=========================================="
echo "Starting Admin API Server"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "Make sure SUPABASE_URL and SUPABASE_KEY are set"
fi

# Start admin API
python admin_api.py

