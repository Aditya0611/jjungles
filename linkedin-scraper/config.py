"""
Configuration constants for LinkedIn Hashtag Scraper
All configurable values are centralized here and can be overridden via environment variables
"""

import os

# ============================================================================
# Platform Configuration
# ============================================================================
PLATFORM_NAME = os.getenv('PLATFORM_NAME', 'linkedin')

# ============================================================================
# Database Configuration
# ============================================================================
SUPABASE_TRENDS_TABLE = os.getenv('SUPABASE_TRENDS_TABLE', 'linkedin')
SUPABASE_LOGS_TABLE = os.getenv('SUPABASE_LOGS_TABLE', 'scrape_logs')

# ============================================================================
# Browser Configuration
# ============================================================================
DEFAULT_LOCALE = os.getenv('BROWSER_LOCALE', 'en-US')
DEFAULT_TIMEZONE = os.getenv('BROWSER_TIMEZONE', 'America/New_York')
DEFAULT_LATITUDE = float(os.getenv('BROWSER_LATITUDE', '40.7128'))  # New York
DEFAULT_LONGITUDE = float(os.getenv('BROWSER_LONGITUDE', '-74.0060'))  # New York

# ============================================================================
# Scraping Configuration
# ============================================================================
DEFAULT_SCROLL_PAUSE_TIME = float(os.getenv('SCROLL_PAUSE_TIME', '1.5'))
DEFAULT_MAX_SCROLLS = int(os.getenv('MAX_SCROLLS', '50'))
DEFAULT_ROTATE_PROXY_EVERY = int(os.getenv('ROTATE_PROXY_EVERY', '10'))

# ============================================================================
# Retry and Timeout Configuration
# ============================================================================
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_BACKOFF_SECONDS = int(os.getenv('RETRY_BACKOFF_SECONDS', '2'))
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '30000'))  # milliseconds
NAVIGATION_TIMEOUT = int(os.getenv('NAVIGATION_TIMEOUT', '60000'))  # milliseconds

# ============================================================================
# Scraping Behavior Configuration
# ============================================================================
NO_NEW_POSTS_THRESHOLD = int(os.getenv('NO_NEW_POSTS_THRESHOLD', '8'))
NO_CHANGE_HEIGHT_THRESHOLD = int(os.getenv('NO_CHANGE_HEIGHT_THRESHOLD', '5'))
MIN_SCROLL_COUNT_FOR_STOP = int(os.getenv('MIN_SCROLL_COUNT_FOR_STOP', '8'))

# ============================================================================
# Output Configuration
# ============================================================================
DEFAULT_OUTPUT_FILE = os.getenv('OUTPUT_FILE', 'trending_hashtags.json')
DEFAULT_DASHBOARD_FILE = os.getenv('DASHBOARD_FILE', 'dashboard_data.js')
DEFAULT_LOG_FILE = os.getenv('LOG_FILE', 'scraper_logs.jsonl')

# ============================================================================
# Hashtag Analysis Configuration
# ============================================================================
TOP_HASHTAGS_COUNT = int(os.getenv('TOP_HASHTAGS_COUNT', '10'))
MIN_HASHTAG_OCCURRENCES = int(os.getenv('MIN_HASHTAG_OCCURRENCES', '1'))
MIN_HASHTAG_LENGTH = int(os.getenv('MIN_HASHTAG_LENGTH', '2'))

# ============================================================================
# Engagement Score Weights (0-100 scale)
# ============================================================================
ENGAGEMENT_FREQUENCY_WEIGHT = float(os.getenv('ENGAGEMENT_FREQUENCY_WEIGHT', '50'))
ENGAGEMENT_DIVERSITY_WEIGHT = float(os.getenv('ENGAGEMENT_DIVERSITY_WEIGHT', '30'))
ENGAGEMENT_SENTIMENT_WEIGHT = float(os.getenv('ENGAGEMENT_SENTIMENT_WEIGHT', '20'))

# Proxy Configuration (Optional)
DEFAULT_PROXY_FILE = os.getenv('PROXY_FILE', 'proxies.txt')
# Set USE_PROXIES to 'false' if running locally without a proxy pool
USE_PROXIES = os.getenv('USE_PROXIES', 'true').lower() == 'true'

# ============================================================================
# Supabase Configuration
# ============================================================================
USE_SUPABASE = os.getenv('USE_SUPABASE', 'true').lower() == 'true'
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')

# ============================================================================
# Authentication Configuration
# ============================================================================
LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL', '')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD', '')

# ============================================================================
# Browser Mode Configuration
# ============================================================================
HEADLESS_MODE = os.getenv('HEADLESS', 'false').lower() == 'true'

# ============================================================================
# Logging Configuration
# ============================================================================
MAX_DASHBOARD_LOG_LINES = int(os.getenv('MAX_DASHBOARD_LOG_LINES', '500'))

# ============================================================================
# Wait Times (seconds)
# ============================================================================
SCROLL_WAIT_MIN = float(os.getenv('SCROLL_WAIT_MIN', '1.0'))
SCROLL_WAIT_MAX = float(os.getenv('SCROLL_WAIT_MAX', '2.5'))
AGGRESSIVE_SCROLL_EXTRA_WAIT = float(os.getenv('AGGRESSIVE_SCROLL_EXTRA_WAIT', '1.5'))
SHOW_MORE_WAIT_MIN = float(os.getenv('SHOW_MORE_WAIT_MIN', '1.0'))
SHOW_MORE_WAIT_MAX = float(os.getenv('SHOW_MORE_WAIT_MAX', '2.0'))
NO_POSTS_WAIT_MIN = float(os.getenv('NO_POSTS_WAIT_MIN', '5.0'))
NO_POSTS_WAIT_MAX = float(os.getenv('NO_POSTS_WAIT_MAX', '8.0'))

# ============================================================================
# Status Constants
# ============================================================================
STATUS_RUNNING = 'running'
STATUS_SUCCESS = 'success'
STATUS_FAILED = 'failed'
STATUS_INTERRUPTED = 'interrupted'

# ============================================================================
# Sentiment Labels
# ============================================================================
SENTIMENT_POSITIVE = 'positive'
SENTIMENT_NEGATIVE = 'negative'
SENTIMENT_NEUTRAL = 'neutral'
