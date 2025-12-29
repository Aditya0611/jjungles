-- ============================================
-- QUICK FIX: Add missing 'caption' column
-- ============================================
-- Copy and paste this ENTIRE file into Supabase SQL Editor and run it
-- This will add the caption column and other missing columns if needed

-- Add caption column
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS caption text NULL;

-- Add language columns if missing
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS language text NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS language_confidence double precision NULL;

-- Add all sentiment analysis columns if missing
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_textblob_polarity double precision NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_textblob_label text NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_vader_compound double precision NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_vader_label text NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_transformer_score double precision NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_transformer_label text NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_consensus_label text NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_average_score double precision NULL;
ALTER TABLE public.linkedin ADD COLUMN IF NOT EXISTS sentiment_scores jsonb NULL;

-- Verify columns were added
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'linkedin' 
  AND column_name IN ('caption', 'language', 'language_confidence', 
                      'sentiment_textblob_polarity', 'sentiment_vader_compound', 
                      'sentiment_transformer_score', 'sentiment_consensus_label')
ORDER BY column_name;

