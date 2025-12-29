# About the Views Column

## Why Views are NULL

The `views` column in your Supabase table shows `NULL` because:

### LinkedIn Feed Limitations

1. **View counts are not visible in the feed**
   - LinkedIn's feed only shows basic post information
   - View counts are only visible to:
     - The post author (on their own posts)
     - When viewing individual post details (not in feed)
   
2. **Privacy and API Restrictions**
   - LinkedIn doesn't expose view counts in the feed HTML
   - View counts require special permissions/API access
   - Even with API access, view counts are limited

3. **What We Can Scrape**
   - ✅ Hashtags
   - ✅ Post text content
   - ✅ Engagement metrics (likes, comments, shares) - if visible
   - ❌ View counts - Not available in feed

### Alternative Solutions

If you need view counts, you would need to:

1. **LinkedIn Official API** (requires partnership/approval)
   - Limited access to view counts
   - Requires business partnership

2. **Individual Post Scraping** (not recommended)
   - Click into each post individually
   - Very slow and likely to get blocked
   - Violates LinkedIn ToS more aggressively

3. **Use Engagement Metrics Instead**
   - Use `posts` field (hashtag occurrence count)
   - Calculate engagement from likes/comments if available
   - Use `engagement_score` (already calculated)

### Current Implementation

The scraper currently:
- Sets `views = NULL` (not available)
- Uses `posts` field to store hashtag occurrence count
- Calculates `engagement_score` based on hashtag frequency
- This is the best we can do with feed scraping

### Recommendation

For your use case (trending hashtags), you don't actually need view counts:
- **Hashtag frequency** (`posts` field) shows popularity
- **Engagement score** shows relative trending
- **Sentiment analysis** shows positive/negative trends

These metrics are sufficient for identifying trending hashtags!

