# TikTok Scraper Delivery Note

## Changes
- **Odoo Scheduler**: Fully integrated. APScheduler script (`worker_apscheduler.py`) is deprecated and removed. Uses Odoo's native `ir.cron`.
- **Widget Filters**: Added "Platform", "Time Range", and "Min Score" filters to the "What's Hot Right Now" Odoo widget.
- **Cleanup**: Removed binary `local_cache.db` and duplicate `client_delivery` folder.

## Verification
- **Path Resolution**: Verified `scheduler_settings.py` correctly locates `base.py`.
- **DB Write**: Verified insertion of records into Supabase `tiktok` table.

## How to Run
1.  **Install Odoo Module**: `odoo_module/social_media_scraper`.
2.  **Configure Credentials**: Ensure `.env` has `SUPABASE_URL` and `SUPABASE_KEY`.
3.  **Run Scraper**: Odoo cron will trigger it automatically (every 3h).
4.  **View Results**: Use the "Social Media & Marketing" dashboard in Odoo.
