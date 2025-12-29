# JJ Trend Widget - Odoo Module

Odoo 16 module for displaying trending social media data from Supabase.

## Quick Start with Docker

```bash
# Start Odoo and PostgreSQL
docker-compose up -d

# Access Odoo
# Open http://localhost:8069 in your browser
```

See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for detailed Docker instructions.

## Manual Installation

See [jj_trend_widget2/SETUP_GUIDE.md](./jj_trend_widget2/SETUP_GUIDE.md) for manual installation steps.

## Recent Updates (December 2024)

### 1. Top 3 Trending Hashtags View
Modified the **"What's Hot Right Now"** view to display only the absolute top 3 trending hashtags across all social media platforms (TikTok, LinkedIn, Twitter, Facebook, YouTube, Instagram), ranked by engagement score.
- Centered, premium card layout with gradient backgrounds.
- Ranking badges (🔥 #1, #2, #3) and platform indicators.
- Simplified interface by removing unnecessary filters for a cleaner dashboard look.

### 2. UI Scrolling Fix
Resolved critical UI issues where the widget content was not scrollable in certain Odoo environments.
- Implemented `max-height: 80vh` with vertical scrolling on the main container.
- Wrapped inline templates in a scroll container for consistent behavior.
- Fixed height constraints that were preventing overflow scrollbars.

### 3. Date Filter Improvements
Optimized the date filtering logic in the backend to handle different date formats and ensure accurate results when filtering by date range in the Admin view.

## Features

- **Raw Trend Data**: Admin dashboard for QA and data filtering
- **What's Hot Right Now**: Client-facing widget for agencies
- Filter by platform, date range, engagement score, and industry
- Real-time data from Supabase

## Project Structure

```
jjungles/
├── docker-compose.yml          # Docker setup
├── odoo.conf                   # Odoo configuration
├── DOCKER_SETUP.md            # Docker documentation
├── jj_trend_widget2/          # Odoo module
│   ├── controllers/           # HTTP controllers
│   ├── models/                # Odoo models
│   ├── views/                 # XML views
│   ├── static/                # JS/XML templates
│   └── SETUP_GUIDE.md         # Detailed setup guide
└── README.md                   # This file
```

## Requirements

- Odoo 16
- PostgreSQL 15
- Python `requests` library
- Supabase account with `trends` table

## Configuration

After installation, configure Supabase credentials in Odoo:
- Settings → Technical → Parameters → System Parameters
- Add `jj_trend.supabase_url` and `jj_trend.supabase_key`

## Documentation

- [Docker Setup Guide](./DOCKER_SETUP.md)
- [Module Setup Guide](./jj_trend_widget2/SETUP_GUIDE.md)
- [Module README](./jj_trend_widget2/README.txt)

## License

LGPL-3

