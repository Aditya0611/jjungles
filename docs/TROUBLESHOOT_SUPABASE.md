# Troubleshooting: Can't See Data in Supabase

## ✅ Your Data IS Being Saved!

The output shows:
```
✅ Successfully saved 10 hashtags to Supabase
   Version ID: 116c0a7a-50ab-4021-88b3-924554e334e1
```

This means the data was successfully inserted!

## 🔍 How to View Your Data in Supabase

### Method 1: Using Supabase Dashboard (Table Editor)

1. **Go to your Supabase Dashboard**
   - Visit: https://app.supabase.com
   - Select your project

2. **Open Table Editor**
   - Click on **"Table Editor"** in the left sidebar
   - Look for the **`linkedin`** table
   - Click on it to view the data

3. **If you don't see the `linkedin` table:**
   - Check if you're in the correct schema (should be `public`)
   - The table might be in a different schema

### Method 2: Using SQL Editor (Recommended)

1. **Open SQL Editor**
   - Click on **"SQL Editor"** in the left sidebar
   - Click **"New Query"**

2. **Run this query to see your data:**
```sql
-- View all records
SELECT * FROM public.linkedin ORDER BY scraped_at DESC LIMIT 20;
```

3. **Check by your latest version ID:**
```sql
SELECT 
    id,
    topic_hashtag,
    engagement_score,
    sentiment_label,
    posts,
    scraped_at
FROM public.linkedin
WHERE version_id = '116c0a7a-50ab-4021-88b3-924554e334e1'
ORDER BY engagement_score DESC;
```

### Method 3: Count Total Records

```sql
-- Count how many records you have
SELECT COUNT(*) as total_records FROM public.linkedin;
```

## 🚨 Common Issues

### Issue 1: Table Doesn't Exist
**Solution:** Run the schema creation SQL:
- Open `linkedin_table_schema.sql`
- Copy and paste into SQL Editor
- Run it

### Issue 2: Wrong Schema
**Solution:** Check if table is in `public` schema:
```sql
SELECT table_name, table_schema 
FROM information_schema.tables 
WHERE table_name = 'linkedin';
```

### Issue 3: Permissions Issue
**Solution:** Check RLS (Row Level Security):
```sql
-- Check if RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'linkedin';

-- If RLS is enabled, you might need to disable it or create policies
-- Or use the service_role key instead of anon key
```

### Issue 4: Looking at Wrong Table
**Solution:** List all tables:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

## 📊 Quick Verification Query

Run this to see everything:
```sql
SELECT 
    id,
    platform,
    topic_hashtag,
    engagement_score,
    sentiment_polarity,
    sentiment_label,
    posts,
    scraped_at,
    version_id,
    metadata->>'caption' as caption,
    metadata->>'language' as language
FROM public.linkedin
ORDER BY scraped_at DESC
LIMIT 10;
```

## 🔧 If Still No Data

1. **Check your `.env` file:**
   - Verify `SUPABASE_URL` is correct
   - Verify `SUPABASE_ANON_KEY` is correct
   - Make sure `USE_SUPABASE=true`

2. **Check Supabase logs:**
   - Go to **"Logs"** → **"Postgres Logs"** in Supabase
   - Look for any errors

3. **Test connection:**
   - Try inserting a test record manually in SQL Editor:
   ```sql
   INSERT INTO public.linkedin (platform, topic_hashtag, engagement_score, sentiment_polarity, sentiment_label, posts, version_id)
   VALUES ('linkedin', '#test', 10.5, 0.5, 'positive', 1, gen_random_uuid());
   ```

4. **Check if data is in a different project:**
   - Make sure you're looking at the correct Supabase project
   - Verify the project URL matches your `.env` file

