-- Quick Fix: Add missing 'caption' column to Supabase linkedin table
-- Run this in your Supabase SQL Editor

-- Add caption column if it doesn't exist
DO $$ 
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                 WHERE table_schema = 'public' 
                 AND table_name = 'linkedin' 
                 AND column_name = 'caption') THEN
    ALTER TABLE public.linkedin ADD COLUMN caption text NULL;
    RAISE NOTICE 'Added caption column successfully';
  ELSE
    RAISE NOTICE 'Caption column already exists';
  END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'linkedin' 
  AND column_name = 'caption';

