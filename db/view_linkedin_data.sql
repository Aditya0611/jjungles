-- View all your LinkedIn hashtag data
-- Run this in Supabase SQL Editor

-- 1. View latest 20 records with all main fields
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
LIMIT 20;

-- 2. View with metadata (caption, language, detailed sentiment)
SELECT 
    id,
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    scraped_at,
    metadata->>'caption' as caption,
    metadata->>'language' as language,
    metadata->'engagement_breakdown' as engagement_details
FROM public.linkedin
ORDER BY scraped_at DESC
LIMIT 10;

-- 3. View top hashtags by engagement score
SELECT 
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    COUNT(*) as occurrences,
    MAX(scraped_at) as last_seen
FROM public.linkedin
GROUP BY topic_hashtag, engagement_score, sentiment_label, posts
ORDER BY engagement_score DESC
LIMIT 20;

-- 4. View data from your latest scraping session
-- Replace 'YOUR_VERSION_ID' with the version_id from your latest run
SELECT 
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    scraped_at
FROM public.linkedin
WHERE version_id = '116c0a7a-50ab-4021-88b3-924554e334e1'  -- Your latest version ID
ORDER BY engagement_score DESC;

-- 5. Summary statistics
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT topic_hashtag) as unique_hashtags,
    COUNT(DISTINCT version_id) as scraping_sessions,
    AVG(engagement_score) as avg_engagement,
    MAX(scraped_at) as latest_scrape,
    MIN(scraped_at) as earliest_scrape
FROM public.linkedin;

