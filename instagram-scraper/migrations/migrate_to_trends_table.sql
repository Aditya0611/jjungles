-- Migration Script: Rename 'instagram' table to 'trends'
-- Run this in your Supabase SQL editor to complete the schema unification

-- Step 1: Rename the table
ALTER TABLE IF EXISTS instagram RENAME TO trends;

-- Step 2: Rename indexes
ALTER INDEX IF EXISTS idx_instagram_topic_hashtag RENAME TO idx_trends_topic_hashtag;
ALTER INDEX IF EXISTS idx_instagram_scraped_at RENAME TO idx_trends_scraped_at;
ALTER INDEX IF EXISTS idx_instagram_engagement_score RENAME TO idx_trends_engagement_score;

-- Step 3: Verify the migration
SELECT 
    'Migration Complete' as status,
    COUNT(*) as total_records,
    MAX(created_at) as latest_record
FROM trends;
