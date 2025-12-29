-- Check if data is being saved to Supabase
-- Run this in your Supabase SQL Editor to verify the data

-- 1. Count total records
SELECT COUNT(*) as total_records FROM public.linkedin;

-- 2. View latest records with all fields
SELECT 
    id,
    platform,
    topic_hashtag,
    engagement_score,
    sentiment_polarity,
    sentiment_label,
    posts,
    views,
    scraped_at,
    version_id
FROM public.linkedin
ORDER BY scraped_at DESC
LIMIT 10;

-- 3. View metadata content (contains caption, language, detailed sentiment)
SELECT 
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    metadata->>'caption' as caption,
    metadata->>'language' as language,
    metadata->'engagement_breakdown' as engagement_details,
    metadata->'sentiment_scores' as sentiment_details
FROM public.linkedin
ORDER BY scraped_at DESC
LIMIT 5;

-- 4. Check by version_id (from your latest run)
SELECT 
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    scraped_at
FROM public.linkedin
WHERE version_id = 'be17ba99-cd79-4a35-a541-470a62672916'
ORDER BY engagement_score DESC;

-- 5. Summary statistics
SELECT 
    COUNT(*) as total_hashtags,
    COUNT(DISTINCT topic_hashtag) as unique_hashtags,
    AVG(engagement_score) as avg_engagement,
    MAX(scraped_at) as latest_scrape,
    MIN(scraped_at) as earliest_scrape
FROM public.linkedin;

