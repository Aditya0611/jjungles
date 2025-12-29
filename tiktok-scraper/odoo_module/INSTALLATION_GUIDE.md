# Odoo Module Installation Guide

## Overview
This guide explains how to install and configure the **Social Media Trend Scraper** Odoo module.

## Module Features

✅ **Dynamic Cron Configuration** - Admin panel to change scraper frequency
✅ **What's Hot Right Now** - Dashboard widget showing trending topics
✅ **Advanced Filters** - Filter by platform, date, and engagement score
✅ **Scheduler Settings** - Enable/disable platforms and set frequency (0.5-24 hours)
✅ **Trend Analytics** - View trending topics with sentiment analysis

## Installation Steps

### 1. Copy Module to Odoo Addons

```bash
# Copy the module to your Odoo addons directory
cp -r odoo_module/social_media_scraper /path/to/odoo/addons/
```

### 2. Update Odoo Apps List

1. Log in to Odoo as Administrator
2. Go to **Apps** menu
3. Click **Update Apps List**
4. Search for "Social Media Trend Scraper"

### 3. Install the Module

1. Find "Social Media Trend Scraper" in the apps list
2. Click **Install**
3. Wait for installation to complete

### 4. Configure Scheduler Settings

1. Go to **Social Media Trends** → **Scheduler Settings**
2. You'll see entries for each platform (TikTok, Instagram, Twitter, etc.)
3. For each platform:
   - Enable/Disable scraping
   - Set frequency (0.5 to 24 hours)
   - Configure metadata (region, headless mode, etc.)

### 5. Sync Settings to Supabase

The module automatically syncs settings to Supabase when you save changes. The worker will pick up the new configuration within 5 minutes (default reload interval).

## Using the Features

### Dynamic Cron Configuration

**Location**: Social Media Trends → Scheduler Settings

**Features**:
- ✅ Enable/disable platforms
- ✅ Set scraping frequency (0.5-24 hours)
- ✅ View run statistics (success rate, last run, next run)
- ✅ Configure metadata (region, headless, upload_to_db)

**Example**:
```
Platform: TikTok
Enabled: Yes
Frequency: 3.0 hours
Success Rate: 95%
Last Run: 2025-12-11 13:43:59
Next Run: 2025-12-11 16:43:59
```

### What's Hot Right Now Widget

**Location**: Dashboard (add widget to your dashboard)

**Features**:
- Shows top 10 trending topics from last 6 hours
- Displays engagement score, posts, views
- Shows sentiment (positive/neutral/negative)
- Platform icons for easy identification
- Auto-refreshes every 6 hours

**To Add to Dashboard**:
1. Go to your Odoo dashboard
2. Click "Add" → "Custom"
3. Select "What's Hot Right Now" widget
4. Save

### Trending Topics View

**Location**: Social Media Trends → Trending Topics

**Views Available**:
- **Kanban** - Card view with hot trends highlighted
- **Tree** - List view with all details
- **Form** - Detailed view of individual trend

**Filters**:

1. **By Engagement Score**:
   - High Engagement (8.0+)
   - Medium Engagement (6.0-7.9)
   - Low Engagement (<6.0)

2. **By Date**:
   - Today
   - Last 7 Days
   - Last 30 Days

3. **By Platform**:
   - TikTok
   - Instagram
   - Twitter/X
   - LinkedIn
   - Facebook

4. **By Sentiment**:
   - Positive
   - Neutral
   - Negative

5. **Special Filters**:
   - Hot Right Now (last 6 hours + score >= 7.0)

**Group By**:
- Platform
- Sentiment
- Scraped Date

## Integration with Worker

The module integrates with the APScheduler worker:

1. **Settings Sync**: When you change settings in Odoo, they're synced to Supabase `scheduler_settings` table
2. **Worker Reload**: Worker reloads settings every 5 minutes (configurable via `WORKER_RELOAD_INTERVAL`)
3. **Automatic Updates**: Worker automatically picks up frequency changes

### Environment Variables

Make sure these are set in your `.env` file:

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key

# Worker Settings
WORKER_ENABLED=true
WORKER_RELOAD_INTERVAL=300  # Reload settings every 5 minutes
SCRAPE_INTERVAL_HOURS=3.0   # Default interval (can be overridden in Odoo)
```

## Database Schema

The module uses two main tables:

### 1. scheduler_settings
- Stores platform configuration
- Synced with Supabase
- Updated from Odoo UI

### 2. social_media_trend
- Stores trending topics
- Populated by scraper
- Queried by Odoo for display

## Troubleshooting

### Settings Not Updating

1. Check Supabase connection in Odoo
2. Verify `sync_to_supabase()` method is called
3. Check worker logs for reload messages

### Widget Not Showing Trends

1. Verify scraper has run recently
2. Check `social_media_trend` table has data
3. Verify `is_hot` field is computed correctly

### Filters Not Working

1. Clear browser cache
2. Restart Odoo server
3. Check search view XML is loaded

## Support

For issues or questions:
1. Check worker logs: `python worker_apscheduler.py`
2. Check Odoo logs: `/var/log/odoo/odoo-server.log`
3. Verify Supabase connection: `python verify_db_writes.py`

## Summary

✅ **Dynamic Cron**: Configure frequency from Odoo UI
✅ **Dashboard Widget**: "What's Hot Right Now" shows trending topics
✅ **Filters**: Platform, Date, Engagement, Sentiment
✅ **Auto-Sync**: Settings automatically sync to worker
✅ **Production-Ready**: Full error handling and validation
