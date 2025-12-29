# Environment Variables Required

## Critical Security Update

**All hardcoded credentials have been removed from the codebase.**

You MUST set the following environment variables for the scraper to work:

## Required Variables

### Instagram Authentication
```bash
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
```

### Supabase Database
```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

## Optional Variables

### Proxy Configuration
```bash
# Single Proxy
PROXY_SERVER=http://proxy.example.com:8080
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=proxy_pass

# Or Proxy Pool (comma-separated)
PROXY_POOL=http://user1:pass1@proxy1.com:8080,http://user2:pass2@proxy2.com:8080
PROXY_MAX_RETRIES=3
```

### Scraping Configuration
```bash
SCROLL_COUNT=15
POSTS_TO_SCAN=400
MIN_HASHTAG_FREQUENCY=1
TOP_HASHTAGS_TO_SAVE=10
POSTS_PER_HASHTAG=3
```

### Schedule Configuration
```bash
SCRAPE_INTERVAL_HOURS=3  # How often to run the scraper
```

## Setup Instructions

### Local Development

1. Create a `.env` file in the project root:
```bash
# .env
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
```

2. The scraper will automatically load from `.env`

### GitHub Actions

1. Go to your repository Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `INSTAGRAM_USERNAME`
   - `INSTAGRAM_PASSWORD`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

### Production/Server

Set environment variables in your deployment platform:

**Heroku:**
```bash
heroku config:set INSTAGRAM_USERNAME="your_username"
heroku config:set INSTAGRAM_PASSWORD="your_password"
heroku config:set SUPABASE_URL="your_url"
heroku config:set SUPABASE_KEY="your_key"
```

**Docker:**
```bash
docker run -e INSTAGRAM_USERNAME="your_username" \
           -e INSTAGRAM_PASSWORD="your_password" \
           -e SUPABASE_URL="your_url" \
           -e SUPABASE_KEY="your_key" \
           your-image
```

## Security Notes

- ⚠️ **NEVER** commit `.env` files to version control
- ✅ The `.env` file is already in `.gitignore`
- ✅ No credentials are hardcoded in the codebase
- ✅ Zip archives exclude `.env` automatically

## Validation

The scraper will validate all required environment variables on startup and fail fast with clear error messages if any are missing.
