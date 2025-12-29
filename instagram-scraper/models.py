import os
import sys
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Local imports
from observability import ErrorCode, metrics

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# -------------------------
# CONSTANTS
# -------------------------
DEFAULT_LANGUAGE = "en"
PLATFORM_NAME = "Instagram"
VERSION_ID = "" # Will be set at runtime
INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"
INSTAGRAM_EXPLORE_URL = "https://www.instagram.com/explore/"
INSTAGRAM_BASE_URL = "https://www.instagram.com"

# Selectors
HOME_SELECTOR = "svg[aria-label='Home']"
SUBMIT_BUTTON_SELECTOR = "button[type='submit']"
PASSWORD_FIELD_SELECTOR = "input[name='password']"
USERNAME_SELECTORS = [
    "input[name='username']",
    "input[aria-label='Phone number, username, or email']",
    "input[aria-label*='username']",
    "input[aria-label*='Username']",
    "input[aria-label*='email']",
    "input[aria-label*='Email']",
    "input[type='text']",
    "input[autocomplete='username']",
    "input[placeholder*='username']",
    "input[placeholder*='Username']",
    "input[placeholder*='email']",
    "input[placeholder*='Email']",
    "input[placeholder*='phone']",
    "input[placeholder*='Phone']"
]
POPUP_SELECTORS = [
    "button:has-text('Not Now')",
    "button:has-text('Not now')",
    "button:has-text('Cancel')"
]
COOKIE_CONSENT_SELECTORS = [
    "button:has-text('Accept')",
    "button:has-text('Accept All')",
    "button:has-text('Allow essential and optional cookies')",
    "button:has-text('Allow all cookies')",
    "button[data-testid='cookie-banner-accept']",
    "button[id*='cookie']",
    "[role='button']:has-text('Accept')",
    "[role='button']:has-text('Allow')"
]

# Timeouts (milliseconds)
TIMEOUT_LOGIN_FORM = 5000
TIMEOUT_LOGIN_SUCCESS = 20000
TIMEOUT_PAGE_NAVIGATION = 60000
TIMEOUT_LOGIN_FALLBACK = 300000
TIMEOUT_POPUP_DISMISS = 3000
TIMEOUT_SELECTOR_WAIT = 5000
TIMEOUT_COOKIE_CONSENT = 3000
TIMEOUT_LOGIN_BUTTON = 10000

# Delays (seconds)
DELAY_PAGE_LOAD = 3
DELAY_LOGIN_WAIT = 2
DELAY_POPUP_DISMISS = 1
DELAY_POST_LOAD_MIN = 2
DELAY_POST_LOAD_MAX = 3
DELAY_TYPING_MIN = 0.5
DELAY_TYPING_MAX = 1.5
DELAY_CREDENTIALS_MIN = 1
DELAY_CREDENTIALS_MAX = 2
DELAY_BETWEEN_HASHTAGS_MIN = 3
DELAY_BETWEEN_HASHTAGS_MAX = 5

# Typing delay (milliseconds)
TYPING_DELAY_MIN = 50
TYPING_DELAY_MAX = 150

# Hashtag Categories
HASHTAG_CATEGORIES = {
    'fashion': ['fashion', 'style', 'ootd', 'outfit', 'fashionista', 'stylish', 'beauty', 'makeup', 'clothing', 'dress', 'shoes', 'accessories'],
    'fitness': ['fitness', 'gym', 'workout', 'health', 'fit', 'exercise', 'training', 'muscle', 'bodybuilding', 'yoga', 'running', 'cycling'],
    'food': ['food', 'foodie', 'cooking', 'recipe', 'delicious', 'yummy', 'instafood', 'foodporn', 'chef', 'restaurant', 'dinner', 'lunch', 'breakfast'],
    'travel': ['travel', 'wanderlust', 'vacation', 'adventure', 'explore', 'trip', 'tourism', 'beach', 'nature', 'mountains', 'travelgram'],
    'technology': ['tech', 'technology', 'gadget', 'innovation', 'digital', 'coding', 'programming', 'ai', 'software', 'hardware', 'app'],
    'business': ['business', 'entrepreneur', 'startup', 'marketing', 'finance', 'investing', 'money', 'success', 'motivation', 'hustle'],
    'entertainment': ['entertainment', 'movie', 'music', 'celebrity', 'artist', 'actor', 'singer', 'concert', 'film', 'show', 'viral', 'trending', 'funny', 'meme'],
    'lifestyle': ['lifestyle', 'life', 'happy', 'love', 'instagood', 'photooftheday', 'picoftheday', 'instagram', 'insta', 'daily', 'inspiration'],
    'photography': ['photography', 'photo', 'photographer', 'camera', 'portrait', 'landscape', 'art', 'creative', 'photoshoot'],
    'sports': ['sports', 'football', 'soccer', 'basketball', 'cricket', 'tennis', 'athlete', 'game', 'player', 'team', 'championship']
}

# -------------------------
# CONFIGURATION
# -------------------------
class Config:
    """Configuration class for Instagram scraper."""
    
    # Environment Check
    ENV: str = os.getenv("ENV", "production").lower()
    IS_DEV: bool = (ENV == "dev")

    # Instagram Credentials
    USERNAME: str = os.getenv("INSTAGRAM_USERNAME", "").strip()
    PASSWORD: str = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    
    # Discovery Settings
    SCROLL_COUNT: int = int(os.getenv("SCROLL_COUNT", "15"))
    POSTS_TO_SCAN: int = int(os.getenv("POSTS_TO_SCAN", "400"))
    MIN_HASHTAG_FREQUENCY: int = int(os.getenv("MIN_HASHTAG_FREQUENCY", "1"))
    TOP_HASHTAGS_TO_SAVE: int = int(os.getenv("TOP_HASHTAGS_TO_SAVE", "10"))
    POSTS_PER_HASHTAG: int = int(os.getenv("POSTS_PER_HASHTAG", "3"))
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Scheduler Configuration
    SCHEDULE_HOURS: int = int(os.getenv("SCHEDULE_HOURS", "3"))
    SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", str(SCHEDULE_HOURS)))
    
    # Trend Lifecycle Configuration
    TREND_EXPIRATION_DAYS: int = int(os.getenv("TREND_EXPIRATION_DAYS", "30"))
    TREND_INACTIVE_DAYS: int = int(os.getenv("TREND_INACTIVE_DAYS", "14"))
    TREND_DECAY_ENABLED: bool = os.getenv("TREND_DECAY_ENABLED", "true").lower() == "true"
    TREND_DECAY_RATE: float = float(os.getenv("TREND_DECAY_RATE", "0.05"))
    TREND_ARCHIVE_ENABLED: bool = os.getenv("TREND_ARCHIVE_ENABLED", "true").lower() == "true"
    
    # Language Detection & Filtering
    ENABLE_LANGUAGE_DETECTION: bool = os.getenv("ENABLE_LANGUAGE_DETECTION", "true").lower() == "true"
    FILTER_LANGUAGES: str = os.getenv("FILTER_LANGUAGES", "")
    MIN_LANGUAGE_CONFIDENCE: float = float(os.getenv("MIN_LANGUAGE_CONFIDENCE", "0.5"))
    
    # Proxy Configuration - STRICT ENFORCEMENT
    # Bypass ONLY allowed if ENV=dev
    REQUIRE_PROXIES: bool = True if ENV != "dev" else (os.getenv("REQUIRE_PROXIES", "true").lower() == "true")
    
    PROXY_SERVER: Optional[str] = os.getenv("PROXY_SERVER")
    PROXY_USERNAME: Optional[str] = os.getenv("PROXY_USERNAME")
    PROXY_PASSWORD: Optional[str] = os.getenv("PROXY_PASSWORD")
    PROXY_BYPASS: str = os.getenv("PROXY_BYPASS", "localhost,127.0.0.1")
    PROXY_MAX_RETRIES: int = int(os.getenv("PROXY_MAX_RETRIES", "50"))
    PROXY_INITIAL_BACKOFF: float = float(os.getenv("PROXY_INITIAL_BACKOFF", "1.0"))
    PROXY_MAX_BACKOFF: float = float(os.getenv("PROXY_MAX_BACKOFF", "60.0"))
    PROXY_ROTATION_STRATEGY: str = os.getenv("PROXY_ROTATION_STRATEGY", "round_robin")
    PROXY_LIST_PATH: str = os.getenv("PROXY_LIST_PATH", "proxies.txt")
    
    # Browser Configuration
    _headless_env = os.getenv("HEADLESS", "").strip().lower()
    _is_ci = os.getenv("CI", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
    
    if _headless_env == "true":
        HEADLESS = True
    elif _headless_env == "false":
        HEADLESS = False
    else:
        HEADLESS = _is_ci
    
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080
    LOCALE: str = "en-US"
    TIMEZONE: str = "Asia/Kolkata"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration values."""
        if not cls.USERNAME or not cls.PASSWORD:
            logging.error(f"[{ErrorCode.CONFIG_MISSING}] Instagram credentials missing")
            metrics.increment('config_validation_failures_total', {'field': 'credentials'})
            return False
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            logging.error(f"[{ErrorCode.CONFIG_MISSING}] Supabase credentials missing")
            metrics.increment('config_validation_failures_total', {'field': 'supabase'})
            return False
        metrics.increment('config_validation_success_total')
        return True

# -------------------------
# DATA MODELS
# -------------------------
@dataclass
class TrendRecord:
    """Data model representing a discovered Instagram trend."""
    platform: str
    url: str
    hashtags: List[str]
    likes: int
    comments: int
    views: int
    shares: int = 0
    reactions: int = 0
    language: str = "en"
    timestamp: datetime = datetime.utcnow()
    engagement_score: float = 0.0
    version: str = ""
    raw_blob: Dict[str, Any] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert TrendRecord to dictionary for database storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['first_seen'] = self.first_seen.isoformat() if self.first_seen else None
        data['last_seen'] = self.last_seen.isoformat() if self.last_seen else None
        return data

    @classmethod
    def from_instagram_data(cls, hashtag_data: Dict, engagement_data: Dict, version_id: str) -> 'TrendRecord':
        """Create TrendRecord from Instagram scraped data."""
        now = datetime.utcnow()
        return cls(
            platform=PLATFORM_NAME,
            url=f"{INSTAGRAM_EXPLORE_URL}tags/{hashtag_data['hashtag']}/",
            hashtags=[f"#{hashtag_data['hashtag']}"],
            likes=int(engagement_data['avg_likes']),
            comments=int(engagement_data['avg_comments']),
            views=int(engagement_data['avg_views']),
            shares=0,
            reactions=0,
            language=engagement_data.get('language_summary', {}).get('primary_language', DEFAULT_LANGUAGE),
            timestamp=now,
            engagement_score=float(engagement_data['avg_engagement']),
            version=version_id,
            raw_blob={
                "category": hashtag_data['category'],
                "frequency": hashtag_data['frequency'],
                "posts_count": hashtag_data['posts_count'],
                "sample_posts": hashtag_data['sample_posts'],
                "discovery_method": "explore_page",
                "avg_likes": engagement_data['avg_likes'],
                "avg_comments": engagement_data['avg_comments'],
                "total_engagement": engagement_data['total_engagement'],
                "total_views": engagement_data['total_views'],
                "video_count": engagement_data.get('video_count', 0),
                "posts_analyzed": Config.POSTS_PER_HASHTAG,
                "total_posts_scanned": Config.POSTS_TO_SCAN,
                "scroll_count": Config.SCROLL_COUNT,
                "min_frequency_threshold": Config.MIN_HASHTAG_FREQUENCY,
                "discovered_at": now.isoformat(),
                "sentiment_summary": engagement_data.get('sentiment_summary', {
                    'positive': 0, 'neutral': 0, 'negative': 0,
                    'avg_polarity': 0.0, 'avg_combined_score': 0.0,
                    'overall_label': 'neutral', 'overall_emoji': '😐'
                }),
                "language_summary": engagement_data.get('language_summary', {
                    'primary_language': DEFAULT_LANGUAGE,
                    'primary_language_percent': 0.0,
                    'primary_language_count': 0,
                    'avg_confidence': 0.0,
                    'detected_count': 0,
                    'total_analyzed': 0,
                    'distribution': {},
                    'detection_rate': 0.0
                }),
                "content_types": engagement_data.get('content_types', {}),
                "primary_format": engagement_data.get('primary_format', 'photo')
            },
            first_seen=now,
            last_seen=now
        )
