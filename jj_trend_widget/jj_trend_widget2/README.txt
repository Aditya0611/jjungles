JJ Trend Engine - Odoo Widget
=============================

Quick Start
-----------
1. Copy the `jj_trend_widget` folder to your Odoo addons directory
2. Restart Odoo server
3. Apps → Update Apps List → Install "JJ Trend Engine"
4. Configure Supabase credentials (see SETUP_GUIDE.md)

Configuration
-------------
Settings → Technical → System Parameters

Add these two parameters:
  jj_trend.supabase_url = https://rnrnbbxnmtajjxscawrc.supabase.co
  jj_trend.supabase_key = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJucm5iYnhubXRhamp4c2Nhd3JjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MzI4OTYsImV4cCI6MjA3MjQwODg5Nn0.WMigmhXcYKYzZxjQFmn6p_Y9y8oNVjuo5YJ0-xzY4h4

Usage
-----
- Trend Engine → Raw Trend Data (Admin view)
- Trend Engine → What's Hot Right Now (Agency widget)

For detailed setup instructions, troubleshooting, and Supabase table schema,
see SETUP_GUIDE.md
