# JJ Trend Widget - Installation & Setup Guide

## Overview
This Odoo 16 module integrates with Supabase to display trending social media data in two views:
- **Raw Trend Data**: Admin dashboard for QA and data filtering
- **What's Hot Right Now**: Client-facing widget for agencies

---

## Installation Methods

### 🐳 Docker (Recommended for Development)

**Quick Start:**
```bash
# From project root
docker-compose up -d
```

Then access Odoo at `http://localhost:8069` and follow the setup wizard.

**For detailed Docker instructions, see:** [DOCKER_SETUP.md](../DOCKER_SETUP.md)

### 📦 Manual Installation

Follow the steps below for manual installation.

---

## Prerequisites

### 1. Supabase Setup
Ensure your Supabase table is set up correctly:

**Table Name**: `trends`

**Required Columns**:
```sql
CREATE TABLE trends (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    engagement_score NUMERIC NOT NULL,
    url TEXT NOT NULL,
    industry TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for better performance
CREATE INDEX idx_trends_platform ON trends(platform);
CREATE INDEX idx_trends_timestamp ON trends(timestamp DESC);
CREATE INDEX idx_trends_engagement ON trends(engagement_score DESC);
```

**Supabase Credentials** (from your README):
- URL: `https://rnrnbbxnmtajjxscawrc.supabase.co`
- Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 2. System Requirements
- Odoo 16
- Python `requests` library (will auto-check on install)

---

## Installation Steps

### Step 1: Copy Module to Odoo
```bash
# Copy the jj_trend_widget folder to your Odoo addons directory
# Common locations:
# - C:\odoo\server\addons\
# - C:\odoo\addons\
# - /opt/odoo/addons/ (Linux)
```

### Step 2: Restart Odoo Server
```bash
# Windows
# Stop and restart your Odoo service from Services panel

# Linux
sudo systemctl restart odoo
```

### Step 3: Update Apps List
1. Login to Odoo
2. Go to **Apps** menu
3. Remove any search filters (click the X)
4. Click **Update Apps List** button (⟳)
5. Search for "JJ Trend"
6. Click **Install**

---

## Configuration

### Enable Developer Mode
1. Go to **Settings**
2. Scroll down to **Developer Tools**
3. Click **Activate the developer mode**

### Configure Supabase Connection
1. Go to **Settings** → **Technical** → **Parameters** → **System Parameters**
2. Click **Create** and add these two parameters:

**Parameter 1:**
- **Key**: `jj_trend.supabase_url`
- **Value**: `https://rnrnbbxnmtajjxscawrc.supabase.co`

**Parameter 2:**
- **Key**: `jj_trend.supabase_key`
- **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJucm5iYnhubXRhamp4c2Nhd3JjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MzI4OTYsImV4cCI6MjA3MjQwODg5Nn0.WMigmhXcYKYzZxjQFmn6p_Y9y8oNVjuo5YJ0-xzY4h4`

3. Click **Save** for each parameter

---

## Usage

### Access the Views

**Admin QA Dashboard (Raw Trend Data)**:
1. Main menu → **Trend Engine** → **Raw Trend Data**
2. Use filters to refine data:
   - Platform (e.g., "instagram", "tiktok")
   - Date range (From/To)
   - Minimum engagement score
3. Click **Apply** to filter

**Agency Widget (What's Hot Right Now)**:
1. Main menu → **Trend Engine** → **What's Hot Right Now**
2. Filter by:
   - Platform (dropdown)
   - Industry (partial text match)
   - Minimum engagement
3. Click **Filter** to update

---

## Troubleshooting

### No Data Showing
1. **Check Supabase credentials**: Verify System Parameters are set correctly
2. **Check Supabase table**: Ensure table `trends` exists and has data
3. **Check Odoo logs**: Look for errors in `/var/log/odoo/odoo.log`
4. **Browser console**: Press F12, check for JavaScript errors

### Template Not Found Error
1. Restart Odoo server
2. Update the module: Apps → JJ Trend Engine → Upgrade
3. Clear browser cache (Ctrl+Shift+R)

### "requests" Module Not Found
```bash
# Install requests library
pip install requests

# Or if using venv:
source /path/to/odoo-venv/bin/activate
pip install requests
```

### Menu Not Showing
1. Check user has proper access rights (base.group_user)
2. Refresh the page
3. Clear browser cache

---

## Data Flow

```
┌─────────────┐
│  Supabase   │
│   Database  │
│  (trends)   │
└──────┬──────┘
       │
       │ REST API
       │
┌──────▼──────────────────────┐
│  trend_service.py           │
│  - Fetches data             │
│  - Applies filters          │
└──────┬──────────────────────┘
       │
       │ RPC Call
       │
┌──────▼──────────────────────┐
│  trend_controller.py        │
│  - /jj_trend/fetch endpoint │
└──────┬──────────────────────┘
       │
       │ JSON Response
       │
┌──────▼──────────────────────┐
│  OWL Components             │
│  - TrendAdminView           │
│  - TrendHotNow              │
└─────────────────────────────┘
```

---

## Sample Data

To test, add sample data to your Supabase `trends` table:

```sql
INSERT INTO trends (platform, timestamp, title, engagement_score, url, industry) VALUES
('instagram', NOW(), 'Top 10 Fitness Tips for 2025', 15432, 'https://instagram.com/p/example1', 'Fitness'),
('tiktok', NOW() - INTERVAL '1 day', 'Viral Dance Challenge', 98765, 'https://tiktok.com/@user/video/123', 'Entertainment'),
('x', NOW() - INTERVAL '2 days', 'Tech News: AI Breakthrough', 5432, 'https://x.com/user/status/456', 'Technology');
```

---

## Support

For issues or questions:
1. Check Odoo logs for detailed error messages
2. Verify Supabase table structure matches requirements
3. Ensure all configuration parameters are correct
