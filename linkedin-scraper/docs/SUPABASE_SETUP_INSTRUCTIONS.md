# Supabase Table Setup Instructions

## Quick Setup

1. **Open Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Select your project: `rnrnbbxnmtajjxscawrc`

2. **Open SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New query"

3. **Run the Schema**
   - Copy the contents of `supabase_schema.sql`
   - Paste into the SQL Editor
   - Click "Run" or press `Ctrl+Enter`

4. **Verify Table Creation**
   - Go to "Table Editor" in the left sidebar
   - You should see the `linkedin` table
   - Check that all columns are present

## Table Schema

The table `linkedin` is designed for LinkedIn hashtag storage:

- **id**: Auto-incrementing primary key
- **platform**: Platform name (e.g., "linkedin", "instagram", "twitter")
- **topic_hashtag**: The hashtag (e.g., "#codingninjas")
- **engagement_score**: Calculated engagement percentage
- **sentiment_polarity**: Sentiment score (-1 to 1)
- **sentiment_label**: "positive", "negative", or "neutral"
- **posts**: Number of post occurrences
- **views**: View count (if available)
- **metadata**: JSON object with additional data
- **scraped_at**: Timestamp of when data was scraped
- **version_id**: Unique ID for each scraping session

## Indexes Created

The following indexes are created for optimal query performance:

1. `idx_instagram_platform` - Fast filtering by platform
2. `idx_instagram_hashtag` - Fast hashtag lookups
3. `idx_instagram_scraped_at` - Time-based queries
4. `idx_instagram_version_id` - Session tracking
5. `idx_instagram_sentiment` - Sentiment filtering
6. `idx_instagram_metadata` - JSON metadata queries (GIN index)

## Security (Optional)

The SQL file includes commented-out RLS (Row Level Security) policies. Uncomment them if you want to:

- Restrict who can insert data
- Control read access
- Implement authentication requirements

## Testing the Table

After creating the table, test it with:

```sql
-- Insert a test record
INSERT INTO public.linkedin (
  platform, 
  topic_hashtag, 
  engagement_score, 
  sentiment_label, 
  posts, 
  version_id
) VALUES (
  'linkedin',
  '#test',
  10.5,
  'neutral',
  5,
  gen_random_uuid()
);

-- Query the test record
SELECT * FROM public.linkedin;
```

## Troubleshooting

### Error: "relation does not exist"
- Make sure you're running the SQL in the correct database
- Check that you're in the `public` schema

### Error: "permission denied"
- Check your Supabase project settings
- Ensure your anon key has the necessary permissions
- You may need to adjust RLS policies

### Error: "duplicate key value"
- The table might already exist
- Use `DROP TABLE IF EXISTS public.linkedin;` first if you want to recreate it

## Next Steps

Once the table is created:

1. ✅ Run the scraper: `python linkedin_hashtag_scraper_playwright.py`
2. ✅ Data will automatically save to Supabase
3. ✅ Query your data using the Supabase dashboard or API

## Useful Queries

### Get Latest Hashtags
```sql
SELECT * FROM linkedin 
ORDER BY scraped_at DESC 
LIMIT 10;
```

### Get Trending Hashtags
```sql
SELECT topic_hashtag, engagement_score, posts, scraped_at
FROM linkedin 
ORDER BY engagement_score DESC 
LIMIT 10;
```

### Get Hashtags by Date Range
```sql
SELECT topic_hashtag, posts, scraped_at
FROM linkedin 
WHERE scraped_at >= NOW() - INTERVAL '7 days'
ORDER BY posts DESC;
```

### Get All Hashtags from a Session
```sql
SELECT * FROM linkedin 
WHERE version_id = 'your-version-id-here'
ORDER BY engagement_score DESC;
```

