-- Add VACUUM/ANALYZE maintenance policy
-- Migration: 008_add_maintenance_policy.sql
-- 
-- This migration sets up automatic maintenance policies for:
-- - VACUUM: Reclaims storage and updates statistics
-- - ANALYZE: Updates query planner statistics
-- - Index maintenance: Keeps indexes optimized

-- ============================================================================
-- AUTOMATIC VACUUM POLICY
-- ============================================================================

-- Enable autovacuum for the tiktok table (default is usually enabled)
-- These settings optimize autovacuum behavior for high-write workloads

ALTER TABLE public.tiktok SET (
    autovacuum_vacuum_scale_factor = 0.1,  -- Vacuum when 10% of table has changed (default: 0.2)
    autovacuum_vacuum_threshold = 1000,    -- Vacuum after 1000 row changes (default: 50)
    autovacuum_analyze_scale_factor = 0.05, -- Analyze when 5% changed (default: 0.1)
    autovacuum_analyze_threshold = 500     -- Analyze after 500 row changes (default: 50)
);

-- ============================================================================
-- MANUAL VACUUM/ANALYZE FUNCTIONS
-- ============================================================================

-- Function to run VACUUM ANALYZE on tiktok table
CREATE OR REPLACE FUNCTION vacuum_analyze_tiktok()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    VACUUM ANALYZE public.tiktok;
    RAISE NOTICE 'VACUUM ANALYZE completed on tiktok table';
END;
$$;

-- Function to run VACUUM FULL (more aggressive, locks table)
CREATE OR REPLACE FUNCTION vacuum_full_tiktok()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    VACUUM FULL ANALYZE public.tiktok;
    RAISE NOTICE 'VACUUM FULL ANALYZE completed on tiktok table';
END;
$$;

-- Function to analyze table and update statistics
CREATE OR REPLACE FUNCTION analyze_tiktok()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    ANALYZE public.tiktok;
    RAISE NOTICE 'ANALYZE completed on tiktok table';
END;
$$;

-- Function to reindex all indexes on tiktok table
CREATE OR REPLACE FUNCTION reindex_tiktok()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REINDEX TABLE public.tiktok;
    RAISE NOTICE 'REINDEX completed on tiktok table';
END;
$$;

-- ============================================================================
-- MAINTENANCE SCHEDULE RECOMMENDATIONS
-- ============================================================================

-- Recommended maintenance schedule:
-- 
-- Daily (low traffic):
--   SELECT analyze_tiktok();
-- 
-- Weekly (medium traffic):
--   SELECT vacuum_analyze_tiktok();
-- 
-- Monthly (high traffic or after large imports):
--   SELECT vacuum_full_tiktok();
--   SELECT reindex_tiktok();
-- 
-- Or use pg_cron extension (if available):
--   SELECT cron.schedule('daily-analyze', '0 2 * * *', 'SELECT analyze_tiktok();');
--   SELECT cron.schedule('weekly-vacuum', '0 3 * * 0', 'SELECT vacuum_analyze_tiktok();');

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Check table bloat and statistics
-- SELECT 
--     schemaname,
--     tablename,
--     n_dead_tup,
--     n_live_tup,
--     last_vacuum,
--     last_autovacuum,
--     last_analyze,
--     last_autoanalyze
-- FROM pg_stat_user_tables
-- WHERE tablename = 'tiktok';

-- Check index usage and bloat
-- SELECT 
--     indexrelname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public' AND tablename = 'tiktok'
-- ORDER BY idx_scan DESC;

-- Check table size
-- SELECT 
--     pg_size_pretty(pg_total_relation_size('public.tiktok')) as total_size,
--     pg_size_pretty(pg_relation_size('public.tiktok')) as table_size,
--     pg_size_pretty(pg_indexes_size('public.tiktok')) as indexes_size;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON FUNCTION vacuum_analyze_tiktok() IS 'Runs VACUUM ANALYZE on tiktok table. Safe to run during operations.';
COMMENT ON FUNCTION vacuum_full_tiktok() IS 'Runs VACUUM FULL ANALYZE on tiktok table. Locks table - run during maintenance window.';
COMMENT ON FUNCTION analyze_tiktok() IS 'Updates query planner statistics for tiktok table. Fast operation.';
COMMENT ON FUNCTION reindex_tiktok() IS 'Rebuilds all indexes on tiktok table. Locks table - run during maintenance window.';

