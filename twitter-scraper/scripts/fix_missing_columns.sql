-- Run this in your Supabase SQL Editor to fix the "comments missing" error
-- and ensure your schema matches the scraper's requirements.

-- 1. Add missing engagement columns
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS comments BIGINT DEFAULT 0;
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS reactions BIGINT DEFAULT 0;

-- 2. Ensure likes/retweets exist (just in case)
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS likes BIGINT DEFAULT 0;
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS retweets BIGINT DEFAULT 0;

-- 3. Ensure sentiment_polarity exists (the code looks for this specifically)
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS sentiment_polarity DOUBLE PRECISION DEFAULT 0;

-- 4. Set defaults for existing null records to prevent errors
UPDATE public.twitter SET comments = 0 WHERE comments IS NULL;
UPDATE public.twitter SET reactions = 0 WHERE reactions IS NULL;
UPDATE public.twitter SET likes = 0 WHERE likes IS NULL;
UPDATE public.twitter SET retweets = 0 WHERE retweets IS NULL;

-- 5. Refresh PostgREST schema cache (CRITICAL step)
-- This tells Supabase to "re-read" the table structure.
NOTIFY pgrst, 'reload schema';

SELECT 'Schema updated successfully! Please run the scraper again.' as message;
