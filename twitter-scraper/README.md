# Twitter Trending Hashtag Scraper & Odoo Integrator

A robust, asynchronous Twitter Trends scraper with Odoo integration for enterprise-grade scheduling and management.

## Features

- **Asynchronous Scraping**: Fetches trends from Trends24 and tweets from Nitter instances without blocking.
- **Sentiment Analysis**: Analyzes hashtag sentiment (Positive/Negative/Neutral) using TextBlob/VADER.
- **Strict Proxy Enforcement**: Mandatory proxy usage with hard-fail logic for security and reliability.
- **Unified Engagement Metrics**: Consistent mapping of Likes, Comments, Views, and Reactions across all platforms.
- **Database Persistence**: Upserts data to Supabase (PostgreSQL) with exponential backoff retries.
- **Odoo Integration**: Unique Odoo module (`twitter_integrator`) to manage scheduling and configuration from the Odoo Admin UI.

## Architecture

1.  **Scraper App (`twitter_scraper_app/`)**: Python package containing the logic.
2.  **Odoo Addon (`odoo_addon/`)**: Standard Odoo module that triggers the scraper execution.
3.  **Supabase**: Backend database storing trend history and run logs.

## Prerequisites

- Python 3.10+
- Odoo 16 or 17 (Enterprise or Community)
- Supabase Project

## Installation

### 1. Scraper Setup

1.  Clone/Unzip this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Create `.env` file in the root based on `.env.example`.

### 2. Odoo Module Setup

1.  Copy the `odoo_addon/twitter_integrator` folder to your Odoo `addons` directory.
2.  Restart Odoo Service.
3.  Go to **Apps**, click **Update App List**.
4.  Search for "Twitter Integrator" and click **Install**.

## Configuration

1.  Navigate to **Settings** > **General Settings** > **Twitter Scraper**.
2.  **Scraper Path**: Enter the full absolute path to this project folder.
3.  **Python Interpreter**: (Optional) Path to your virtualenv python.
4.  **Schedule Frequency**: Adjust how often the scraper runs (default: Every 4 hours).
5.  Click **Save**.

### Proxy Enforcement (Strict Mode)

The scraper strictly enforces proxy usage to prevent bypass and IP leaks.
- **No Bypass**: The scraper will **fail at startup** if no proxies are configured.
- **Hard-Fail**: Immediate termination on proxy blocks (403, 407, 429) to avoid un-proxied retries.
- **Configuration**: Provide comma-separated proxies in `PROXY_LIST` (e.g., `http://user:pass@host:port`).

## Verification

### Manual Run (CLI)
```bash
python t3_scraper.py
```
Check standard output for structured JSON logs.

### Developer Tools

The `scripts/` directory contains utility scripts:
- `check_heartbeat.py`: Verifies the latest data sync in Supabase.
- `verify_table_columns.py`: Checks if your Supabase schema matches the unified model.
- `migration_v2.sql`: SQL script to add missing `comments` and `reactions` columns.

## Database Schema (Unified Model)

| Column | Type | Description |
|--------|------|-------------|
| `topic_hashtag` | Text | The trending hashtag |
| `sentiment_label` | Text | Positive, Negative, or Neutral |
| `engagement_score` | Double | Unified 0-10 impact score |
| `posts` | BigInt | Number of posts/tweets |
| `views` | BigInt | Number of views |
| `likes` | BigInt | Number of likes |
| `comments` | BigInt | Number of comments |
| `reactions` | BigInt | Number of reactions |
| `metadata` | JSONB | Links and post content snippets |
| `scraped_at` | Timestamptz | When the record was last updated |

## Troubleshooting

- **"No proxies loaded"**: You must provide valid proxies in `.env`.
- **"Invalid port"**: Ensure your proxy format is correct (`host:port`).
- **"Table not found"**: Ensure you have run the initial SQL and `migration_v2.sql` in Supabase.
