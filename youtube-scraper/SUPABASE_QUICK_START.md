# Supabase Quick Start Guide

## Step 1: Create the Table in Supabase

1. Go to your Supabase project: https://rnrnbbxnmtajjxscawrc.supabase.co
2. Navigate to **SQL Editor**
3. Copy and paste the SQL from `supabase_setup.sql`
4. Click **Run** to create the `trends` table and indexes

## Step 2: Configure Environment Variables

Create a `.env` file in the project root with:

```env
# Required
YOUTUBE_API_KEY=your_youtube_api_key
USE_DATABASE=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
python -m textblob.download_corpora
```

## Step 4: Run the Scraper

```bash
python main.py --locales US --limit 50
```

The scraper will:
- ✅ Collect hashtags from YouTube videos
- ✅ Calculate engagement scores
- ✅ Perform sentiment analysis
- ✅ Store data in Supabase `trends` table
- ✅ Export to JSON files

## Verify Data in Supabase

1. Go to Supabase Dashboard → **Table Editor**
2. Select the `trends` table
3. View your scraped hashtag data with sentiment analysis!

## Table Schema

The `trends` table includes:
- `platform` - "youtube"
- `topic_hashtag` - The hashtag text
- `engagement_score` - 0-100 score
- `sentiment_polarity` - -1.0 to 1.0
- `sentiment_label` - 'positive', 'negative', or 'neutral'
- `posts` - Number of videos using this hashtag
- `views` - Average views per video
- `metadata` - JSON with additional info
- `scraped_at` - Timestamp
- `version_id` - UUID for batch tracking

