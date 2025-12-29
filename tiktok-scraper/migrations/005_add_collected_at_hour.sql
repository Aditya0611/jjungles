-- Add collected_at_hour column if it doesn't exist
-- Migration: 005_add_collected_at_hour.sql
-- 
-- This migration adds the collected_at_hour column for hourly deduplication.
-- Run this if you get an error about missing 'collected_at_hour' column.

-- Add collected_at_hour column if it doesn't exist
ALTER TABLE public.tiktok 
ADD COLUMN IF NOT EXISTS collected_at_hour TIMESTAMP WITH TIME ZONE NULL;

-- Add unique constraint for hourly deduplication (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_tiktok_topic_hour'
    ) THEN
        ALTER TABLE public.tiktok 
        ADD CONSTRAINT uq_tiktok_topic_hour 
        UNIQUE (topic, collected_at_hour);
    END IF;
END $$;

-- Create index if not exists
CREATE INDEX IF NOT EXISTS idx_tiktok_topic_collected_at_hour 
ON public.tiktok USING BTREE (topic, collected_at_hour);

-- Add comment
COMMENT ON COLUMN public.tiktok.collected_at_hour IS 'Hour bucket for deduplication (truncated to hour)';

