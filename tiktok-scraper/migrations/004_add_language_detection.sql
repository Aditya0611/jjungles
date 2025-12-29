-- Add language detection support to unified schema
-- Migration: 004_add_language_detection.sql
-- 
-- This migration adds dedicated language detection columns to the unified schema:
-- - language: ISO 639-1 language code (e.g., 'en', 'es', 'fr', 'de', 'zh', 'ja')
-- - language_confidence: Detection confidence score (0.0-1.0)
--
-- Language detection uses langdetect library for dynamic detection across all platforms.
-- These columns enable efficient querying and filtering by language.

-- Add language columns
ALTER TABLE public.tiktok 
ADD COLUMN IF NOT EXISTS language TEXT NULL;

ALTER TABLE public.tiktok 
ADD COLUMN IF NOT EXISTS language_confidence DOUBLE PRECISION NULL;

-- Create indexes for language queries
CREATE INDEX IF NOT EXISTS idx_tiktok_language 
ON public.tiktok USING BTREE (language) 
WHERE language IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tiktok_language_confidence 
ON public.tiktok USING BTREE (language_confidence DESC) 
WHERE language_confidence IS NOT NULL;

-- Composite index for language + platform queries
CREATE INDEX IF NOT EXISTS idx_tiktok_platform_language 
ON public.tiktok USING BTREE (platform, language) 
WHERE language IS NOT NULL;

-- Composite index for language + engagement score (for trending by language)
CREATE INDEX IF NOT EXISTS idx_tiktok_language_engagement 
ON public.tiktok USING BTREE (language, engagement_score DESC) 
WHERE language IS NOT NULL;

-- Add column comments
COMMENT ON COLUMN public.tiktok.language IS 'Detected language code (ISO 639-1 format) using langdetect. Examples: en, es, fr, de, zh, ja, pt, ru, ar, hi';
COMMENT ON COLUMN public.tiktok.language_confidence IS 'Language detection confidence score (0.0-1.0). Higher values indicate more confident detection.';

-- Update metadata comment to note language is also stored in dedicated columns
COMMENT ON COLUMN public.tiktok.metadata IS 'Additional metadata including trend_lifecycle, category, caption, title, post_format, sound, tags, and source_url. Language is also stored in dedicated language and language_confidence columns for efficient querying.';

-- Example queries for language-based analysis:

-- Find trending hashtags by language
-- SELECT topic, engagement_score, language, language_confidence
-- FROM public.tiktok
-- WHERE language = 'en'
--   AND scraped_at > NOW() - INTERVAL '24 hours'
-- ORDER BY engagement_score DESC
-- LIMIT 20;

-- Find high-confidence multi-language trends
-- SELECT language, COUNT(*) as trend_count, AVG(engagement_score) as avg_score
-- FROM public.tiktok
-- WHERE language_confidence > 0.7
--   AND scraped_at > NOW() - INTERVAL '24 hours'
-- GROUP BY language
-- ORDER BY trend_count DESC;

-- Find trends with low language confidence (may need review)
-- SELECT topic, language, language_confidence, engagement_score
-- FROM public.tiktok
-- WHERE language_confidence < 0.5
--   AND language IS NOT NULL
--   AND scraped_at > NOW() - INTERVAL '24 hours'
-- ORDER BY engagement_score DESC;

