# Database Migration Guide

## Overview

This guide explains how to run database migrations to set up the required tables, indexes, and functions for the scraper system.

## Migration Files

All migrations are in the `migrations/` directory and must be run in order:

1. `002_create_tiktok_table.sql` - Base table structure
2. `003_add_trend_lifecycle_tracking.sql` - Trend lifecycle indexes
3. `004_add_language_detection.sql` - Language detection columns
4. `005_add_collected_at_hour.sql` - Hourly deduplication
5. `006_add_daily_snapshots.sql` - Daily snapshot support
6. `007_add_covering_indexes.sql` - Performance indexes
7. `008_add_maintenance_policy.sql` - VACUUM/ANALYZE functions
8. `009_create_scheduler_settings.sql` - Scheduler settings table

## Quick Start

### Option 1: Supabase SQL Editor (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. For each migration file:
   - Open the migration file (e.g., `migrations/006_add_daily_snapshots.sql`)
   - Copy the entire SQL content
   - Paste into SQL Editor
   - Click **Run**

### Option 2: Migration Runner Script

```bash
# List all migrations
python run_migrations.py

# Show specific migration SQL
python run_migrations.py 006_add_daily_snapshots.sql
```

The script will display the SQL that needs to be run.

### Option 3: psql (PostgreSQL Client)

```bash
# Connect to Supabase database
psql 'postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres'

# Run migrations in order
\i migrations/002_create_tiktok_table.sql
\i migrations/003_add_trend_lifecycle_tracking.sql
\i migrations/004_add_language_detection.sql
\i migrations/005_add_collected_at_hour.sql
\i migrations/006_add_daily_snapshots.sql
\i migrations/007_add_covering_indexes.sql
\i migrations/008_add_maintenance_policy.sql
\i migrations/009_create_scheduler_settings.sql
```

## Required Migrations for Scheduler

To use the automated scheduler, you need at minimum:

1. **Base table** (`002_create_tiktok_table.sql`) - Required
2. **Scheduler settings** (`009_create_scheduler_settings.sql`) - Required for scheduler

Optional but recommended:
- `006_add_daily_snapshots.sql` - For daily snapshots
- `004_add_language_detection.sql` - For language detection
- `007_add_covering_indexes.sql` - For performance

## Migration Details

### 002_create_tiktok_table.sql
Creates the main `tiktok` table with:
- Basic columns (platform, topic, engagement_score, etc.)
- Indexes for performance
- Unique constraint for hourly deduplication

### 003_add_trend_lifecycle_tracking.sql
Adds indexes for trend lifecycle analysis (data stored in JSONB metadata).

### 004_add_language_detection.sql
Adds `language` and `language_confidence` columns for language detection.

### 005_add_collected_at_hour.sql
Adds `collected_at_hour` column and unique constraint for hourly deduplication.

### 006_add_daily_snapshots.sql
Adds `snapshot_date` and `snapshot_version` columns for daily snapshots.

### 007_add_covering_indexes.sql
Adds covering indexes for faster queries (index-only scans).

### 008_add_maintenance_policy.sql
Creates VACUUM/ANALYZE functions and configures autovacuum.

### 009_create_scheduler_settings.sql
Creates `scheduler_settings` table and functions for:
- Platform configuration
- Frequency settings
- Run statistics
- Admin management

## Verifying Migrations

### Check if table exists:

```sql
-- Check if scheduler_settings exists
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'scheduler_settings'
);

-- Check if snapshot columns exist
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'tiktok' 
AND column_name IN ('snapshot_date', 'snapshot_version');
```

### Check migration status:

```sql
-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check scheduler_settings
SELECT * FROM scheduler_settings;
```

## Troubleshooting

### Error: Table already exists

If a table already exists, migrations use `IF NOT EXISTS` clauses, so they're safe to run multiple times.

### Error: Column already exists

Migrations use `ADD COLUMN IF NOT EXISTS`, so they're idempotent.

### Error: Function already exists

Migrations use `CREATE OR REPLACE FUNCTION`, so functions are updated if they exist.

### Supabase Schema Cache

If you see "Could not find the table in the schema cache" errors:
1. Run the migration in Supabase SQL Editor
2. Wait a few seconds for schema cache to refresh
3. The error should resolve automatically

## Running Migrations in Production

1. **Backup first**: Always backup your database before running migrations
2. **Test in staging**: Run migrations in a test environment first
3. **Run during low traffic**: Schedule migrations during maintenance windows
4. **Monitor**: Watch for errors and verify tables/columns were created

## Next Steps

After running migrations:

1. **Verify scheduler settings**:
   ```sql
   SELECT * FROM scheduler_settings;
   ```

2. **Start scheduler**:
   ```bash
   python scheduler.py
   ```

3. **Test admin API** (optional):
   ```bash
   python admin_api.py
   curl http://localhost:5000/api/settings
   ```

---

**Status**: ✅ Migration files ready
**Order**: Must run migrations in sequence (002 → 009)

