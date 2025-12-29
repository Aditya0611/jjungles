#!/usr/bin/env python3
"""
Unified Social Media Scraper Core
Standardized across platforms with consistent logging, robust error handling, 
proxy rotation, and unified data schema (SocialMediaRecord).
"""

import asyncio
import random
import math
import time
import json
import tempfile
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import os
import re
from supabase import Client
import uuid
from typing import Optional, List, Dict, Any
from contextlib import nullcontext
import logging
from supabase_utils import (
    SocialMediaRecord, init_supabase, upload_to_supabase, 
    convert_to_numeric, get_historical_trend_data, 
    analyze_trend_lifecycle, validate_social_media_record
)

# Load environment variables from .env file (must be before reading env vars)
try:
    from dotenv import load_dotenv
    # Load .env file if it exists
    env_loaded = load_dotenv()
except ImportError:
    env_loaded = False

# Import JobQueue for retry logic (optional)
try:
    from job_queue import JobQueue
    JOB_QUEUE_AVAILABLE = True
except ImportError:
    JOB_QUEUE_AVAILABLE = False
    JobQueue = None

# Import structured logging and metrics
USE_JSON_LOGGING = os.environ.get("USE_JSON_LOGGING", "false").lower() == "true"  # Default to false for readable output

try:
    from logging_metrics import (
        setup_json_logging, TraceContext, Span, log_error, metrics,
        get_trace_context, log_with_trace, trace_request, ProxyBlockedError
    )
    setup_json_logging(level=logging.INFO, use_json=USE_JSON_LOGGING)
except ImportError:
    # Fallback to basic logging if module not available
    USE_JSON_LOGGING = False
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create stub functions
    class TraceContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def create_span(self, *args): return self
    
    class Span:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
    
    def log_error(error, context=None, logger=None):
        if logger is None: logger = logging.getLogger(__name__)
        logger.error(f"Error: {error}", exc_info=error)
        return type('ErrorInfo', (), {'category': type('Category', (), {'value': 'unknown'})})()
    
    
    class ProxyBlockedError(Exception): pass
    
    def get_trace_context(): return None
    
    def log_with_trace(level, message, **kwargs):
        logger = logging.getLogger(__name__)
        logger.log(level, message)
    
    def trace_request(*args, **kwargs): return TraceContext()
    
    metrics = type('Metrics', (), {
        'increment': lambda *args, **kwargs: None,
        'set_gauge': lambda *args, **kwargs: None,
        'observe_histogram': lambda *args, **kwargs: None,
        'get_all_metrics': lambda: {}
    })()

# Import proxy pool
try:
    from proxy_pool import (
        ProxyPool, ProxyConfig, create_proxy_pool_from_env, use_proxy
    )
    PROXY_POOL_AVAILABLE = True
except ImportError:
    PROXY_POOL_AVAILABLE = False
    ProxyPool = None
    ProxyConfig = None

# Import Local Cache
try:
    from cache_manager import LocalCache
    LOCAL_CACHE_AVAILABLE = True
    local_cache = LocalCache()
except ImportError:
    LOCAL_CACHE_AVAILABLE = False
    local_cache = None
    logger.warning("LocalCache not available")
    create_proxy_pool_from_env = None
    use_proxy = None

logger = logging.getLogger(__name__)

# Log .env status after logging is configured
if env_loaded:
    logger.info("Loaded environment variables from .env file")
elif os.path.exists('.env'):
    logger.warning(".env file exists but may be empty or invalid. Check your SUPABASE_URL and SUPABASE_KEY")
else:
    logger.warning(".env file not found. Create .env file with SUPABASE_URL and SUPABASE_KEY")

# ============================================================================
# STANDARDIZED DATA MODEL - Imported from supabase_utils
# ============================================================================

# Sentiment analysis imports (optional dependencies)
TEXTBLOB_AVAILABLE = False
VADER_AVAILABLE = False
TRANSFORMER_AVAILABLE = False
LANGDETECT_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
    logger.info("TextBlob sentiment analysis available")
except ImportError:
    logger.warning("TextBlob not available. Install with: pip install textblob")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
    logger.info("VADER sentiment analysis available (recommended for social media)")
except ImportError:
    logger.warning("VADER not available. Install with: pip install vaderSentiment")

# Transformer model (optional, for advanced sentiment analysis)
USE_TRANSFORMER = os.environ.get("USE_TRANSFORMER_SENTIMENT", "false").lower() == "true"
if USE_TRANSFORMER:
    try:
        from transformers import pipeline
        TRANSFORMER_AVAILABLE = True
        logger.info("Transformer sentiment analysis enabled")
    except ImportError:
        logger.warning("Transformers not available. Install with: pip install transformers torch")

# Language detection
try:
    from langdetect import detect, detect_langs, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    LANGDETECT_AVAILABLE = True
    # Set seed for consistent results
    DetectorFactory.seed = 0
    logger.info("Language detection enabled")
except ImportError:
    logger.warning("langdetect not available. Install with: pip install langdetect")

# Centralized selector configuration with fallbacks
SELECTORS = {
    'hashtag_tab': [
        "text=Hashtags",
        "[data-e2e='hashtag-tab']",
        "button:has-text('Hashtags')",
        "a:has-text('Hashtags')",
        "[role='tab']:has-text('Hashtag')"
    ],
    'view_more_button': [
        "text=/view more/i",
        "button:has-text('View more')",
        "[data-e2e='view-more-button']",
        ".view-more-btn"
    ],
    'hashtag_item': [
        "[data-testid*='hashtag_item']",
        "[data-e2e*='hashtag']",
        ".hashtag-item",
        "[class*='HashtagItem']"
    ],
    'post_format': [
        "[data-e2e*='video']",
        "[data-e2e*='image']",
        "[class*='video']",
        "[class*='image']",
        "video",
        "img"
    ],
    'sound_info': [
        "[data-e2e*='sound']",
        "[data-e2e*='audio']",
        "[class*='sound']",
        "[class*='audio']",
        "[aria-label*='sound']",
        "[aria-label*='audio']"
    ],
    'body': ['body']
}

# Configuration constants
MAX_VIEW_MORE_CLICKS = 25  # Cap to avoid infinite loops
MIN_WAIT_SEC = 2.0  # Minimum wait between actions
MAX_WAIT_SEC = 5.0  # Maximum wait between actions
MAX_RETRIES = 3  # Number of retry attempts
BASE_BACKOFF_SEC = 2.0  # Base backoff for exponential retry
CHUNK_SIZE = int(os.environ.get("BATCH_CHUNK_SIZE", "100"))  # Chunk size for Supabase upserts (default: 100, max: 1000)
MAX_BATCH_SIZE = 1000  # Maximum batch size (Supabase limit)
BATCH_RETRY_ATTEMPTS = 3  # Number of retry attempts for failed batches
BATCH_RETRY_DELAY = 1.0  # Delay between batch retries (seconds)
MIN_HASHTAGS_THRESHOLD = 10  # Minimum hashtags to consider scrape successful
TOP_N_UPLOAD_THRESHOLD = 10  # Number of top records to upload
ERROR_MSG_NO_HASHTAGS = "No hashtag elements found"
SCRAPE_RETRY_THRESHOLD = 30  # Minimum elements to accept valid scrape
DEFAULT_CATEGORY = "General"

# Supabase Configuration (loaded from .env file)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

# Log status of environment variables (without exposing values)
if SUPABASE_URL and SUPABASE_KEY:
    logger.info("Supabase credentials loaded from environment")
elif SUPABASE_URL or SUPABASE_KEY:
    logger.warning("Supabase credentials partially set - check .env file")
else:
    logger.warning("Supabase credentials not set - add SUPABASE_URL and SUPABASE_KEY to .env file")

# Proxy Configuration (mandatory for TikTok)
# REQUIRE_PROXIES env var ignored - enforcement is now mandatory properly
REQUIRE_PROXIES = True
PROXY_SERVER = os.environ.get("PROXY_SERVER")  # e.g., "http://proxy.example.com:8080"
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")

# Initialize proxy pool if available
_global_proxy_pool = None
if PROXY_POOL_AVAILABLE:
    try:
        _global_proxy_pool = create_proxy_pool_from_env()
        if _global_proxy_pool:
            logger.info(f"Proxy pool initialized with {len(_global_proxy_pool.proxies)} proxies")
        elif PROXY_SERVER:
            # Fallback: create pool from single proxy env vars
            from proxy_pool import ProxyConfig, ProxyPool
            proxy_config = ProxyConfig(
                server=PROXY_SERVER,
                username=PROXY_USERNAME,
                password=PROXY_PASSWORD,
            )
            _global_proxy_pool = ProxyPool(proxies=[proxy_config])
            logger.info("Proxy pool initialized from environment variables")
    except Exception as e:
        logger.warning(f"Failed to initialize proxy pool: {e}")
        _global_proxy_pool = None

# Alternate URLs to try if primary fails
ALTERNATE_URLS = [
    "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/{region}",
    "https://www.tiktok.com/business/en/inspiration/popular/hashtag/pc/{region}",
]

def validate_proxy_requirements() -> tuple[bool, Optional[str]]:
    """
    Validate proxy requirements before scraping.
    
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
        - (True, None) if validation passes
        - (False, error_message) if validation fails
    """

    
    logger.info("Validating proxy requirements (Enforced)...")
    
    # Check if proxy pool is available
    if not PROXY_POOL_AVAILABLE:
        error_msg = (
            "REQUIRE_PROXIES=true but proxy_pool module not available. "
            "Install with: pip install -r requirements.txt"
        )
        logger.error(error_msg)
        return False, error_msg
    
    if not _global_proxy_pool or len(_global_proxy_pool.proxies) == 0:
        error_msg = (
            "REQUIRE_PROXIES=true but no proxies configured.\n"
            "Please set one of the following in your .env file:\n"
            "  - PROXY_SERVER=http://your-proxy.com:8080\n"
            "  - PROXY_LIST=http://proxy1.com:8080,http://proxy2.com:8080\n"
            "Or set REQUIRE_PROXIES=false to disable proxy enforcement."
        )
        logger.error(error_msg)
        return False, error_msg
    
    # Check if at least one proxy is healthy and available
    try:
        available_proxies = _global_proxy_pool._get_available_proxies()
        if not available_proxies:
            error_msg = (
                f"REQUIRE_PROXIES=true but no healthy proxies available.\n"
                f"Total proxies: {len(_global_proxy_pool.proxies)}, Available: 0\n"
                "All proxies may be in cooldown or have failed health checks.\n"
                "Check proxy configuration or wait for proxies to recover."
            )
            logger.error(error_msg)
            return False, error_msg
        
        logger.info(f"✅ Proxy validation passed: {len(available_proxies)} healthy proxies available")
        return True, None
        
    except Exception as e:
        error_msg = f"Error validating proxy availability: {e}"
        logger.error(error_msg)
        return False, error_msg


def jittered_wait(min_sec: float = MIN_WAIT_SEC, max_sec: float = MAX_WAIT_SEC) -> float:
    """Return a random wait time with jitter to mimic human behavior."""
    wait_time = random.uniform(min_sec, max_sec)
    return wait_time






async def wait_for_page_load(page, max_wait=60):
    """Wait for page to fully load with multiple checks"""
    logger.info("Waiting for page to load completely...")
    
    # Wait for title to be non-empty
    for i in range(max_wait):
        title = await page.title()
        if title and len(title) > 0:
            logger.info(f"Page title loaded: {title}")
            break
        await asyncio.sleep(1)
        if i % 10 == 0 and i > 0:
            logger.info(f"Still waiting... ({i}s)")
    
    # Wait for body element with fallbacks
    for selector in SELECTORS['body']:
        try:
            await page.wait_for_selector(selector, timeout=30000)
            logger.info("Body element found")
            break
        except PlaywrightTimeout:
            logger.warning(f"Timeout waiting for body element with selector: {selector}")
            continue
    
    # Additional wait for JavaScript with jitter
    wait_time = jittered_wait(3.0, 6.0)
    await asyncio.sleep(wait_time)
    
    # Verify hashtag content
    content = await page.content()
    has_hashtag_content = "hashtag" in content.lower()
    logger.info(f"Hashtag content detected: {has_hashtag_content}")
    
    return has_hashtag_content

async def ensure_hashtags_tab(page):
    """Ensure we're on the hashtags tab using centralized selectors with fallbacks"""
    logger.info("Checking if we're on hashtags page...")
    
    content = await page.content()
    
    # Check if we're on songs page
    is_on_songs = any(x in content.lower() for x in ['pocketful of sunshine', 'trending songs'])
    
    if is_on_songs:
        logger.info("Currently on songs page, clicking Hashtags tab...")
        try:
            # Use centralized selectors with fallbacks
            for selector in SELECTORS['hashtag_tab']:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        logger.info(f"Clicked Hashtags tab using selector: {selector}")
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        wait_time = jittered_wait(3.0, 6.0)
                        await asyncio.sleep(wait_time)
                        return True
                except Exception as e:
                    logger.debug(f"Failed with selector {selector}: {e}")
                    continue
            
            logger.warning("Could not find Hashtags tab to click after trying all selectors")
            return False
        except Exception as e:
            logger.error(f"Error clicking Hashtags tab: {e}")
            return False
    else:
        logger.info("Already on hashtags page")
        return True

async def click_view_more_buttons(page, max_clicks=MAX_VIEW_MORE_CLICKS):
    """Click View More buttons with capped clicks and jittered waits.
    
    Uses centralized selectors with fallbacks and human-like timing.
    """
    total_clicks = 0
    consecutive_failures = 0
    
    logger.info(f"Starting to click View More buttons (max: {max_clicks})...")
    
    for attempt in range(1, max_clicks + 1):
        try:
            button = None
            # Try each selector until we find a button
            for selector in SELECTORS['view_more_button']:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        logger.debug(f"Found View More button with selector: {selector}")
                        break
                except:
                    continue
            
            if not button:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.info(f"No button found for {consecutive_failures} attempts, stopping")
                    break
                wait_time = jittered_wait(1.5, 3.0)
                await asyncio.sleep(wait_time)
                continue
            
            is_visible = await button.is_visible()
            
            if not is_visible:
                logger.info(f"Button not visible at attempt {attempt}, stopping")
                break
            
            consecutive_failures = 0
            
            # Scroll button into view with jitter
            await button.scroll_into_view_if_needed()
            wait_time = jittered_wait(0.8, 1.5)
            await asyncio.sleep(wait_time)
            
            # Click with fallback
            try:
                await button.click(force=True, timeout=5000)
            except:
                await button.evaluate("el => el.click()")
            
            total_clicks += 1
            
            if total_clicks % 10 == 0:
                logger.info(f"Progress: {total_clicks} clicks")
            
            # Wait for content to load with jitter
            wait_time = jittered_wait(4.0, 7.0)
            await asyncio.sleep(wait_time)
            
            # Scroll down periodically to help load content
            if total_clicks % 5 == 0:
                await page.evaluate("window.scrollBy(0, 300)")
                wait_time = jittered_wait(1.5, 3.0)
                await asyncio.sleep(wait_time)
                
        except Exception as e:
            logger.debug(f"Error at attempt {attempt}: {e}")
            consecutive_failures += 1
            if consecutive_failures >= 3:
                break
    
    logger.info(f"Clicked View More {total_clicks} times")
    return total_clicks

def calculate_engagement_score(hashtag: str, posts: str, category: str, element_text: str) -> float:
    """Calculate engagement score (1-10) using log-scaling to resist outliers.
    
    Uses logarithmic transformation of post counts to prevent extreme values
    from dominating the score. Final score is clamped between 1.0 and 10.0.
    
    Args:
        hashtag: The hashtag text
        posts: Post count as string (e.g., '1.5K', '2.3M')
        category: Category of the hashtag
        element_text: Full text of the element
    
    Returns:
        Float between 1.0 and 10.0
    """
    try:
        base_score = 5.0
        
        # Log-scaled post count contribution
        if posts and posts != "N/A":
            posts_num = convert_to_numeric(posts)
            if posts_num and posts_num > 0:
                # Use log10 to scale: log10(1000) = 3, log10(1M) = 6, log10(1B) = 9
                # Scale to contribute roughly 0-4 points
                log_posts = math.log10(posts_num)
                post_score = min(4.0, log_posts / 2.0)  # Cap at 4 points
                base_score += post_score
        
        # Category bonus (smaller impact)
        high_engagement_categories = ['Entertainment', 'Music', 'Dance', 'Comedy']
        medium_engagement_categories = ['Sports & Fitness', 'Food & Cooking', 'Fashion & Beauty']
        
        if category in high_engagement_categories:
            base_score += 0.5
        elif category in medium_engagement_categories:
            base_score += 0.3
        
        # Hashtag characteristics
        if hashtag:
            hashtag_lower = hashtag.lower()
            trending_keywords = ['viral', 'trending', 'challenge', 'fyp', 'foryou']
            for keyword in trending_keywords:
                if keyword in hashtag_lower:
                    base_score += 0.3
                    break
            
            # Short hashtags are often more memorable
            if len(hashtag) <= 10:
                base_score += 0.2
            elif len(hashtag) > 25:
                base_score -= 0.2
        
        # Clamp between 1.0 and 10.0
        final_score = max(1.0, min(10.0, base_score))
        return round(final_score, 1)
        
    except Exception as e:
        logger.debug(f"Error calculating engagement score: {e}")
        return 5.0

# Initialize sentiment analyzers (lazy loading)
_vader_analyzer = None
_transformer_pipeline = None

def _get_vader_analyzer():
    """Get or create VADER sentiment analyzer instance."""
    global _vader_analyzer
    if _vader_analyzer is None and VADER_AVAILABLE:
        _vader_analyzer = SentimentIntensityAnalyzer()
    return _vader_analyzer

def _get_transformer_pipeline():
    """Get or create transformer sentiment pipeline."""
    global _transformer_pipeline
    if _transformer_pipeline is None and TRANSFORMER_AVAILABLE:
        try:
            _transformer_pipeline = pipeline("sentiment-analysis", 
                                            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                                            device=-1)  # Use CPU by default
            logger.info("Transformer sentiment pipeline initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize transformer pipeline: {e}")
            return None
    return _transformer_pipeline

def extract_caption_title(element_text: str, hashtag: str) -> tuple[Optional[str], Optional[str]]:
    """Extract caption and title from element text.
    
    Args:
        element_text: Full text content from the scraped element
        hashtag: The hashtag being processed
    
    Returns:
        Tuple of (caption: Optional[str], title: Optional[str])
    """
    caption = None
    title = None
    
    # Try to extract caption (usually longer text after hashtag and stats)
    # Pattern: hashtag, stats, then caption text
    patterns = [
        r'{}\s+[\d\.]+[KM]?\s+Posts\s+(.+)'.format(re.escape(hashtag)),
        r'{}\s+(.+)'.format(re.escape(hashtag)),
        r'Posts\s+(.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            potential_caption = match.group(1).strip()
            # Filter out numeric patterns and short text
            if len(potential_caption) > 10 and not re.match(r'^[\d\s\.KM]+$', potential_caption):
                caption = potential_caption[:500]  # Limit length
                break
    
    # Title is often the hashtag itself or first few words of caption
    if caption:
        words = caption.split()[:5]  # First 5 words
        title = ' '.join(words) if words else hashtag
    else:
        title = hashtag
    
    return caption, title

def detect_language(text: Optional[str], fallback_text: Optional[str] = None, 
                    additional_texts: Optional[List[str]] = None) -> tuple[Optional[str], Optional[float]]:
    """Detect language from text using langdetect (dynamic detection across all platforms).
    
    This function uses the langdetect library to dynamically detect the language of content
    across all social media platforms. It combines multiple text sources for better accuracy.
    
    Args:
        text: Primary text to analyze (caption or title)
        fallback_text: Fallback text if primary is too short
        additional_texts: Optional list of additional text sources (hashtags, tags, etc.)
    
    Returns:
        Tuple of (language_code: Optional[str], confidence: Optional[float])
        Language code is ISO 639-1 format (e.g., 'en', 'es', 'fr', 'de', 'zh', 'ja', 'pt', 'ru', 'ar', 'hi')
        Confidence is 0.0-1.0, where higher values indicate more confident detection
    
    Examples:
        >>> detect_language("Hello world, this is a test", "Test caption")
        ('en', 0.95)
        >>> detect_language("Hola mundo", "Spanish content")
        ('es', 0.92)
    """
    if not LANGDETECT_AVAILABLE:
        logger.debug("langdetect not available, skipping language detection")
        return None, None
    
    # Collect all text sources
    text_sources = []
    if text and text.strip():
        text_sources.append(text.strip())
    if fallback_text and fallback_text.strip():
        text_sources.append(fallback_text.strip())
    if additional_texts:
        for additional in additional_texts:
            if additional and additional.strip():
                text_sources.append(additional.strip())
    
    # Combine all text sources for better detection
    text_to_analyze = None
    if text_sources:
        # Try longest text first (usually most reliable)
        sorted_sources = sorted(text_sources, key=len, reverse=True)
        for source in sorted_sources:
            if len(source) >= 10:  # Minimum length for reliable detection
                text_to_analyze = source
                break
        
        # If no single source is long enough, combine them
        if not text_to_analyze:
            combined = " ".join(sorted_sources)
            if len(combined.strip()) >= 10:
                text_to_analyze = combined.strip()
    
    if not text_to_analyze:
        logger.debug("No sufficient text for language detection")
        return None, None
    
    try:
        # Detect language using langdetect
        detected_lang = detect(text_to_analyze)
        
        # Get confidence scores for all languages
        try:
            lang_probs = detect_langs(text_to_analyze)
            if lang_probs:
                # Find the probability of the detected language
                confidence = next((prob.prob for prob in lang_probs if prob.lang == detected_lang), 0.0)
                
                # Only return if confidence is reasonable (>0.3)
                # Lower threshold allows more detections while filtering out very uncertain ones
                if confidence > 0.3:
                    logger.debug(f"Detected language: {detected_lang} (confidence: {confidence:.3f})")
                    return detected_lang, round(confidence, 3)
                else:
                    logger.debug(f"Language detection confidence too low: {confidence:.3f} for '{detected_lang}'")
                    return None, None
            else:
                # Fallback: return detected language with default confidence
                logger.debug(f"Detected language: {detected_lang} (default confidence: 0.5)")
                return detected_lang, 0.5
        except Exception as e:
            # Fallback: return detected language with default confidence
            logger.debug(f"Could not get language probabilities: {e}, using default confidence")
            return detected_lang, 0.5
    
    except LangDetectException as e:
        # Language detection failed (e.g., insufficient text, ambiguous)
        logger.debug(f"Language detection exception: {e}")
        return None, None
    except Exception as e:
        logger.debug(f"Language detection error: {e}")
        return None, None

def extract_post_format(element, element_text: str, platform: str = "TikTok") -> str:
    """Extract post format type (video, image, etc.) from element.
    
    For TikTok Creative Center, we use heuristics since the listing page doesn't show
    individual post formats. TikTok is primarily video-based, so we default to "video"
    but check for indicators of other formats.
    
    Args:
        element: BeautifulSoup element object
        element_text: Full text content from the scraped element
        platform: Platform name (default: TikTok)
    
    Returns:
        Format type string: "video", "image", "carousel", "live", or "video" (default for TikTok)
    """
    # TikTok is primarily a video platform, so default to video
    format_type = "video"
    
    # Check HTML attributes and structure for format indicators
    if element:
        # Check for video indicators
        video_indicators = [
            element.find('video'),
            element.find(attrs={'data-e2e': re.compile(r'video', re.I)}),
            element.find(attrs={'class': re.compile(r'video', re.I)}),
            element.find(attrs={'data-testid': re.compile(r'video', re.I)}),
        ]
        if any(video_indicators):
            # Check if it's a live video
            if element.find(string=re.compile(r'live|streaming|LIVE', re.I)):
                format_type = "live"
            else:
                format_type = "video"
        
        # Check for image indicators
        elif element.find('img') or element.find(attrs={'data-e2e': re.compile(r'image|photo', re.I)}):
            # Check if multiple images (carousel)
            images = element.find_all('img')
            if images and len(images) > 1:
                format_type = "carousel"
            else:
                format_type = "image"
        
        # Check for live indicators in attributes
        live_indicators = [
            element.find(attrs={'data-e2e': re.compile(r'live', re.I)}),
            element.find(attrs={'class': re.compile(r'live', re.I)}),
        ]
        if any(live_indicators):
            format_type = "live"
    
    # Check text patterns for format hints
    text_lower = element_text.lower()
    if 'live' in text_lower or 'streaming' in text_lower or '🔴' in element_text:
        format_type = "live"
    elif 'carousel' in text_lower or 'multiple' in text_lower or 'slideshow' in text_lower:
        format_type = "carousel"
    elif 'photo' in text_lower or 'picture' in text_lower or 'image' in text_lower:
        format_type = "image"
    elif 'video' in text_lower or '🎬' in element_text:
        format_type = "video"
    
    # For TikTok, if we couldn't determine, default to video (TikTok's primary format)
    if format_type == "unknown" and platform.lower() == "tiktok":
        format_type = "video"
    
    return format_type

def extract_sound_info(element, element_text: str, hashtag: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Extract sound/audio information from element.
    
    For TikTok Creative Center, we try to extract sound information from available
    HTML elements and text patterns. Sound information is critical for TikTok virality
    as trending sounds drive content creation.
    
    Args:
        element: BeautifulSoup element object
        element_text: Full text content from the scraped element
        hashtag: Optional hashtag text for context
    
    Returns:
        Dictionary with sound information:
        {
            'sound_name': Optional[str],
            'artist': Optional[str],
            'sound_id': Optional[str],
            'original_sound': Optional[bool]
        }
    """
    sound_info = {
        'sound_name': None,
        'artist': None,
        'sound_id': None,
        'original_sound': False
    }
    
    if not element:
        return sound_info
    
    # Try to find sound information in HTML attributes
    sound_elements = []
    
    # Look for sound-related elements using multiple strategies
    for selector in SELECTORS['sound_info']:
        try:
            found = element.select(selector)
            if found:
                sound_elements.extend(found)
        except:
            continue
    
    # Also check for common sound data attributes
    sound_attrs = element.find_all(attrs={
        'data-e2e': re.compile(r'sound|audio|music', re.I)
    })
    sound_elements.extend(sound_attrs)
    
    # Check for sound in data attributes (TikTok often uses data-* attributes)
    for attr_name in ['data-sound', 'data-audio', 'data-music', 'data-track']:
        attr_value = element.get(attr_name)
        if attr_value:
            sound_info['sound_name'] = str(attr_value)[:200]
            break
    
    # Extract from sound elements
    for sound_elem in sound_elements:
        # Get text content
        sound_text = sound_elem.get_text(strip=True)
        if sound_text and len(sound_text) > 2:
            sound_info['sound_name'] = sound_text[:200]  # Limit length
            break
        
        # Get from attributes
        for attr in ['title', 'aria-label', 'alt', 'data-title', 'data-sound-name', 'data-audio-name']:
            attr_value = sound_elem.get(attr, '')
            if attr_value and len(attr_value) > 2:
                sound_info['sound_name'] = attr_value[:200]
                break
    
    # Extract from element text using patterns
    text_lower = element_text.lower()
    
    # Pattern: "original sound - Artist Name" or "Sound - Song Name"
    sound_patterns = [
        r'original\s+sound[:\s-]+(.+?)(?:\s*-\s*(.+))?',
        r'sound[:\s-]+(.+?)(?:\s*-\s*(.+))?',
        r'audio[:\s-]+(.+?)(?:\s*-\s*(.+))?',
        r'music[:\s-]+(.+?)(?:\s*-\s*(.+))?',
        r'🎵\s*(.+?)(?:\s*-\s*(.+))?',
        r'🎶\s*(.+?)(?:\s*-\s*(.+))?',
    ]
    
    for pattern in sound_patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            if not sound_info['sound_name']:
                sound_info['sound_name'] = match.group(1).strip()[:200]
            if match.lastindex >= 2 and match.group(2):
                sound_info['artist'] = match.group(2).strip()[:100]
            
            # Check if original sound
            if 'original' in match.group(0).lower():
                sound_info['original_sound'] = True
            break
    
    # Try to extract sound ID from data attributes
    sound_id_patterns = [
        r'sound[_-]?id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)',
        r'audio[_-]?id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in sound_id_patterns:
        match = re.search(pattern, str(element), re.IGNORECASE)
        if match:
            sound_info['sound_id'] = match.group(1)
            break
    
    # Clean up sound name (remove common prefixes)
    if sound_info['sound_name']:
        sound_name = sound_info['sound_name']
        # Remove common prefixes
        prefixes = ['sound:', 'audio:', 'music:', 'original sound:', 'original audio:']
        for prefix in prefixes:
            if sound_name.lower().startswith(prefix):
                sound_name = sound_name[len(prefix):].strip()
        sound_info['sound_name'] = sound_name[:200]
    
    return sound_info

def analyze_sentiment(hashtag: str, element_text: str, caption: Optional[str] = None, 
                     title: Optional[str] = None, method: str = "auto") -> tuple[float, str]:
    """Analyze sentiment using TextBlob, VADER, or transformer models.
    
    Priority order (if method="auto"):
    1. Transformer (if available and USE_TRANSFORMER=true)
    2. VADER (if available)
    3. TextBlob (if available)
    4. Fallback to neutral
    
    Args:
        hashtag: The hashtag text
        element_text: Full text of the element
        caption: Optional caption text to analyze (preferred over element_text)
        title: Optional title text to include in analysis
        method: Sentiment method to use ("auto", "vader", "textblob", "transformer")
    
    Returns:
        Tuple of (polarity: float, label: str)
        Polarity ranges from -1.0 (negative) to 1.0 (positive)
        Label is one of: "Positive", "Neutral", "Negative"
    """
    # Build text to analyze from multiple sources (prefer meaningful content)
    text_sources = []
    
    # Add caption if available and meaningful
    if caption and len(caption.strip()) > 5:
        text_sources.append(caption.strip())
    
    # Add title if available and meaningful
    if title and len(title.strip()) > 3 and title != hashtag:
        text_sources.append(title.strip())
    
    # Clean element_text - remove numbers, "Posts", etc. to get meaningful content
    if element_text:
        # Remove common patterns: "1.2K Posts", "Posts", numbers, etc.
        cleaned_element = re.sub(r'\d+\.?\d*[KM]?\s*Posts?', '', element_text, flags=re.IGNORECASE)
        cleaned_element = re.sub(r'^\d+\s*', '', cleaned_element)  # Remove leading rank numbers
        cleaned_element = cleaned_element.strip()
        # Only use if it has meaningful words (not just hashtag and numbers)
        if cleaned_element and len(cleaned_element) > 5 and not re.match(r'^[#\d\s\.KM]+$', cleaned_element):
            text_sources.append(cleaned_element)
    
    # Combine all text sources
    if text_sources:
        text_to_analyze = " ".join(text_sources)
    else:
        # Fallback: use hashtag name itself (hashtags can have sentiment: #love, #hate, #amazing)
        # Remove # symbol for better analysis
        hashtag_clean = hashtag.replace('#', '').strip()
        if hashtag_clean and len(hashtag_clean) >= 2:
            text_to_analyze = hashtag_clean
        else:
            return 0.0, "Neutral"
    
    if not text_to_analyze or len(text_to_analyze.strip()) < 2:
        return 0.0, "Neutral"
    
    # Clean text for analysis - remove extra whitespace
    text_to_analyze = re.sub(r'\s+', ' ', text_to_analyze.strip())
    
    # Method priority: transformer > vader > textblob > fallback
    if method == "auto":
        # Try transformer first (if enabled)
        if USE_TRANSFORMER and TRANSFORMER_AVAILABLE:
            try:
                pipeline = _get_transformer_pipeline()
                if pipeline:
                    result = pipeline(text_to_analyze[:512])  # Limit input length
                    if isinstance(result, list):
                        result = result[0]
                    
                    label_map = {
                        "POSITIVE": "Positive",
                        "NEGATIVE": "Negative",
                        "NEUTRAL": "Neutral",
                        "LABEL_0": "Negative",
                        "LABEL_1": "Neutral",
                        "LABEL_2": "Positive"
                    }
                    
                    label = label_map.get(result.get("label", ""), "Neutral")
                    score = result.get("score", 0.5)
                    
                    # Convert score to polarity (-1 to 1)
                    if label == "Positive":
                        polarity = score
                    elif label == "Negative":
                        polarity = -score
                    else:
                        polarity = (score - 0.5) * 2  # Scale to -1 to 1
                    
                    return float(polarity), label
            except Exception as e:
                logger.debug(f"Transformer sentiment failed: {e}, falling back to VADER")
        
        # Try VADER (best for social media text)
        if VADER_AVAILABLE:
            try:
                analyzer = _get_vader_analyzer()
                if analyzer:
                    scores = analyzer.polarity_scores(text_to_analyze)
                    compound = scores['compound']
                    
                    # Use more sensitive thresholds for better detection
                    # VADER compound scores: positive (>0.05), neutral (-0.05 to 0.05), negative (<-0.05)
                    # Lower threshold to 0.03 to catch more positive/negative sentiments
                    if compound >= 0.03:
                        label = "Positive"
                        polarity = compound
                    elif compound <= -0.03:
                        label = "Negative"
                        polarity = compound
                    else:
                        # For very neutral scores, check individual components
                        if scores['pos'] > scores['neg'] * 1.5:
                            label = "Positive"
                            polarity = scores['pos'] * 0.5  # Scale to reasonable range
                        elif scores['neg'] > scores['pos'] * 1.5:
                            label = "Negative"
                            polarity = -scores['neg'] * 0.5
                        else:
                            label = "Neutral"
                            polarity = compound
                    
                    logger.debug(f"VADER sentiment: {label} (compound={compound:.3f}, pos={scores['pos']:.3f}, neg={scores['neg']:.3f}) for text: {text_to_analyze[:50]}")
                    return float(polarity), label
            except Exception as e:
                logger.debug(f"VADER sentiment failed: {e}, falling back to TextBlob")
        
        # Try TextBlob
        if TEXTBLOB_AVAILABLE:
            try:
                blob = TextBlob(text_to_analyze)
                polarity = blob.sentiment.polarity
                
                # Use more sensitive thresholds (lower from 0.1 to 0.05)
                if polarity > 0.05:
                    label = "Positive"
                elif polarity < -0.05:
                    label = "Negative"
                else:
                    # Check subjectivity for borderline cases
                    subjectivity = blob.sentiment.subjectivity
                    if subjectivity > 0.3:  # If subjective, trust the polarity more
                        if polarity > 0.02:
                            label = "Positive"
                        elif polarity < -0.02:
                            label = "Negative"
                        else:
                            label = "Neutral"
                    else:
                        label = "Neutral"
                
                logger.debug(f"TextBlob sentiment: {label} (polarity={polarity:.3f}, subjectivity={subjectivity:.3f}) for text: {text_to_analyze[:50]}")
                return float(polarity), label
            except Exception as e:
                logger.debug(f"TextBlob sentiment failed: {e}")
    
    # Specific method selection
    elif method == "vader" and VADER_AVAILABLE:
        analyzer = _get_vader_analyzer()
        if analyzer:
            scores = analyzer.polarity_scores(text_to_analyze)
            compound = scores['compound']
            if compound >= 0.05:
                return float(compound), "Positive"
            elif compound <= -0.05:
                return float(compound), "Negative"
            else:
                return float(compound), "Neutral"
    
    elif method == "textblob" and TEXTBLOB_AVAILABLE:
        blob = TextBlob(text_to_analyze)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return float(polarity), "Positive"
        elif polarity < -0.1:
            return float(polarity), "Negative"
        else:
            return float(polarity), "Neutral"
    
    elif method == "transformer" and TRANSFORMER_AVAILABLE:
        pipeline = _get_transformer_pipeline()
        if pipeline:
            result = pipeline(text_to_analyze[:512])
            if isinstance(result, list):
                result = result[0]
            label_map = {
                "POSITIVE": "Positive",
                "NEGATIVE": "Negative",
                "NEUTRAL": "Neutral"
            }
            label = label_map.get(result.get("label", ""), "Neutral")
            score = result.get("score", 0.5)
            polarity = score if label == "Positive" else (-score if label == "Negative" else (score - 0.5) * 2)
            return float(polarity), label
    
    # Fallback: Check hashtag for common sentiment words if no analyzer available
    hashtag_lower = hashtag.lower().replace('#', '')
    
    # Common positive hashtag words
    positive_words = ['love', 'amazing', 'awesome', 'best', 'great', 'happy', 'joy', 'wonderful', 
                      'beautiful', 'fantastic', 'excellent', 'perfect', 'incredible', 'favorite',
                      'win', 'success', 'celebrate', 'blessed', 'grateful', 'proud', 'excited',
                      'fun', 'funny', 'hilarious', 'cute', 'adorable', 'sweet', 'inspirational']
    
    # Common negative hashtag words
    negative_words = ['hate', 'worst', 'terrible', 'awful', 'horrible', 'sad', 'angry', 'frustrated',
                     'disappointed', 'fail', 'failure', 'problem', 'issue', 'bad', 'wrong', 'stupid',
                     'annoying', 'disgusting', 'depressed', 'anxious', 'scared', 'fear', 'worried']
    
    if any(word in hashtag_lower for word in positive_words):
        logger.debug(f"Hashtag-based sentiment: Positive (hashtag: {hashtag})")
        return 0.3, "Positive"
    elif any(word in hashtag_lower for word in negative_words):
        logger.debug(f"Hashtag-based sentiment: Negative (hashtag: {hashtag})")
        return -0.3, "Negative"
    
    # Final fallback to neutral
    logger.debug(f"No sentiment analyzer available and no sentiment keywords found, returning neutral for: {text_to_analyze[:50]}")
    return 0.0, "Neutral"

async def scrape_with_retry(page, max_retries=2):
    """Scrape with retry logic if too few hashtags found"""
    
    for retry in range(max_retries):
        logger.info(f"\n{'='*60}")
        logger.info(f"SCRAPE ATTEMPT {retry + 1}/{max_retries}")
        logger.info(f"{'='*60}\n")
        
        # Scroll to reveal content with jitter
        logger.info("Scrolling to reveal content...")
        for i in range(8):
            await page.evaluate("window.scrollBy(0, 500)")
            wait_time = jittered_wait(0.8, 1.5)
            await asyncio.sleep(wait_time)
        
        # Click View More buttons (capped at MAX_VIEW_MORE_CLICKS)
        total_clicks = await click_view_more_buttons(page)
        
        # Extended scrolling with pauses
        logger.info("Extended scrolling to load all content...")
        for i in range(15):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            wait_time = jittered_wait(1.2, 2.0)
            await asyncio.sleep(wait_time)
            
            # Extra View More checks during scrolling
            if i % 5 == 0 and i > 0:
                logger.info(f"Checking for more View More buttons... (scroll {i})")
                extra_clicks = await click_view_more_buttons(page, max_clicks=10)
                if extra_clicks > 0:
                    total_clicks += extra_clicks
        
        # Final wait with jitter
        logger.info("Final wait before parsing...")
        wait_time = jittered_wait(5.0, 8.0)
        await asyncio.sleep(wait_time)
        
        # Parse content using centralized selectors
        page_source = await page.content()
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Try each selector until we find hashtag elements
        hashtag_elements = []
        for selector in SELECTORS['hashtag_item']:
            hashtag_elements = soup.select(selector)
            if hashtag_elements:
                logger.debug(f"Found elements using selector: {selector}")
                break
        
        logger.info(f"Found {len(hashtag_elements)} hashtag elements")
        
        # If we got a good number, return
        if len(hashtag_elements) >= SCRAPE_RETRY_THRESHOLD:
            logger.info("Good collection, proceeding with parsing")
            return hashtag_elements, page_source
        
        # If this is the last retry, accept what we have
        if retry == max_retries - 1:
            logger.info(f"Final attempt - accepting {len(hashtag_elements)} elements")
            return hashtag_elements, page_source
        
        # Otherwise, reload and try again
        logger.warning(f"Only found {len(hashtag_elements)} elements, reloading page...")
        await page.reload(wait_until='networkidle', timeout=60000)
        wait_time = jittered_wait(8.0, 12.0)
        await asyncio.sleep(wait_time)
        await ensure_hashtags_tab(page)
        wait_time = jittered_wait(3.0, 6.0)
        await asyncio.sleep(wait_time)
    
    return [], ""

async def scrape_single_attempt(browser, url: str, debug: bool = True, use_proxy: bool = False) -> tuple[List[Dict[str, Any]], str]:
    """Perform a single scrape attempt with a fresh browser context.
    
    Returns tuple of (scraped_data, page_source)
    """
    # Start tracing
    trace_context = get_trace_context()
    span = trace_context.create_span("scrape_single_attempt") if trace_context else None
    if span:
        span.__enter__()
    
    try:
        # Increment attempt counter
        metrics.increment("scrape_attempts_total", labels={"use_proxy": str(use_proxy)})
        
        scraped_data = []
        seen_hashtags = set()
        
        # Enhanced browser context with stealth features
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': ['geolocation'],
            'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},  # New York
            'color_scheme': 'light',
            'java_script_enabled': True,
            'bypass_csp': True,
            'ignore_https_errors': True,
            'extra_http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        # Add proxy if configured and requested
        proxy_used = None
        if use_proxy:
            if _global_proxy_pool:
                # Use proxy pool
                proxy_config_obj = _global_proxy_pool.get_proxy()
                if proxy_config_obj:
                    proxy_used = proxy_config_obj
                    context_options['proxy'] = proxy_config_obj.to_playwright_config()
                    log_with_trace(logging.INFO, "Using proxy from pool", 
                                  proxy_server=proxy_config_obj.server,
                                  proxy_key=_global_proxy_pool._get_proxy_key(proxy_config_obj))
            elif PROXY_SERVER:
                # Fallback to single proxy from env
                proxy_config = {'server': PROXY_SERVER}
                if PROXY_USERNAME and PROXY_PASSWORD:
                    proxy_config['username'] = PROXY_USERNAME
                    proxy_config['password'] = PROXY_PASSWORD
                context_options['proxy'] = proxy_config
                log_with_trace(logging.INFO, "Using proxy from environment", proxy_server=PROXY_SERVER)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        # Add stealth scripts to avoid detection
        await page.add_init_script("""
            // Override the navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins to appear more realistic
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Add chrome property
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        try:
            log_with_trace(logging.INFO, "Navigating to TikTok Creative Center", url=url)
            
            # Add random mouse movements before navigation to appear more human
            try:
                await page.mouse.move(random.randint(100, 300), random.randint(100, 300))
                await asyncio.sleep(random.uniform(0.1, 0.3))
            except:
                pass
            
            # Navigate with increased timeout and networkidle for better reliability
            try:

                response = await page.goto(url, wait_until='networkidle', timeout=90000)
                
                # Explicitly check for blocks
                if response:
                    status = response.status
                    if status in [403, 429]:
                        raise ProxyBlockedError(f"Access blocked by target (Status: {status})")
                    
                    # Check for "Access Denied" or Captcha text
                    content = await page.content()
                    if "captcha" in content.lower() or "access denied" in content.lower():
                         raise ProxyBlockedError("Captcha or Access Denied detected in page content")

            except PlaywrightTimeout:
                log_with_trace(logging.WARNING, "Timeout with networkidle, trying domcontentloaded")
                response = await page.goto(url, wait_until='domcontentloaded', timeout=90000)
                
                # Check response again if successful
                if response:
                    status = response.status
                    if status in [403, 429]:
                        raise ProxyBlockedError(f"Access blocked by target (Status: {status})")
            
            # Wait for page load
            page_loaded = await wait_for_page_load(page, max_wait=30)
            
            if not page_loaded:
                log_with_trace(logging.WARNING, "Page may not have loaded properly")
            
            log_with_trace(logging.INFO, "Page loaded", url=page.url, title=await page.title())
            
            # Ensure hashtags tab
            await ensure_hashtags_tab(page)
            wait_time = jittered_wait(3.0, 6.0)
            await asyncio.sleep(wait_time)
            
            # Scrape with retry logic
            hashtag_elements, page_source = await scrape_with_retry(page, max_retries=2)
            
            if debug:
                debug_filename = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                debug_file = os.path.join(tempfile.gettempdir(), debug_filename)
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                log_with_trace(logging.INFO, "Debug file saved", debug_file=debug_file)
            
            if not hashtag_elements:
                log_with_trace(logging.ERROR, ERROR_MSG_NO_HASHTAGS)
                await context.close()
                return [], ""
            
            log_with_trace(logging.INFO, f"Processing {len(hashtag_elements)} elements",
                          elements_count=len(hashtag_elements))

            # Process elements
            for i, element in enumerate(hashtag_elements):
                try:
                    element_text = element.get_text(strip=True)
                    
                        # Extract data
                    hashtag = None
                    posts = None
                    rank = None
                    category = DEFAULT_CATEGORY
                    
                    # Rank
                    rank_match = re.search(r'^(\d+)', element_text)
                    if rank_match:
                        rank = int(rank_match.group(1))
                    
                    # Hashtag
                    patterns = [
                        r'\d+#\s*([a-zA-Z]+?)(?=[A-Z][a-z])',
                        r'\d+#\s*([a-zA-Z]+?)(?=\d)',
                        r'\d+#\s*([a-zA-Z]+?)(?=[A-Z])',
                        r'\d+#\s*([a-zA-Z]+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, element_text)
                        if match:
                            word = match.group(1)
                            
                            # Filter songs
                            song_words = ['pocketful', 'sunshine', 'feeling', 'trolls']
                            if len(word) >= 3 and word.isalpha() and not any(s in word.lower() for s in song_words):
                                hashtag = f"#{word}"
                                break
                    
                    # Posts
                    posts_patterns = [
                        r'(\d+\.?\d*)\s*[MB]?\s*Posts',  # Support decimals and M/B
                        r'(\d+)\s*K\s*Posts',
                        r'(\d+)\s*Posts',
                    ]
                    
                    for pattern in posts_patterns:
                        match = re.search(pattern, element_text)
                        if match:
                            num = match.group(1)
                            if 'M' in match.group(0):
                                posts = f"{num}M"
                            elif 'B' in match.group(0):
                                posts = f"{num}B"
                            elif 'K' in match.group(0):
                                posts = f"{num}K"
                            else:
                                posts = num
                            break
                    
                    if not hashtag or hashtag in seen_hashtags:
                        continue
                    
                    seen_hashtags.add(hashtag)
                    
                    # Extract caption and title
                    caption, title = extract_caption_title(element_text, hashtag)
                    
                    # Detect language from caption/title/hashtag (dynamic detection across all platforms)
                    # Include hashtag as additional text source for better detection
                    language, language_confidence = detect_language(
                        caption, 
                        title, 
                        additional_texts=[hashtag] if hashtag else None
                    )
                    
                    # Extract post format (critical for TikTok virality analysis)
                    # TikTok is primarily video, but we check for other formats
                    post_format = extract_post_format(element, element_text, platform="TikTok")
                    
                    # Extract sound/audio information (critical for TikTok virality - trending sounds drive content)
                    sound_info = extract_sound_info(element, element_text, hashtag=hashtag)
                    sound_name = sound_info.get('sound_name')
                    sound_artist = sound_info.get('artist')
                    sound_id = sound_info.get('sound_id')
                    original_sound = sound_info.get('original_sound', False)
                    
                    # Scores - analyze sentiment on caption/title/hashtag (use all available text)
                    engagement = calculate_engagement_score(hashtag, posts, category, element_text)
                    polarity, sentiment = analyze_sentiment(hashtag, element_text, caption=caption, title=title)
                    
                    scraped_data.append({
                        "rank": rank if rank else "N/A",
                        "hashtag": hashtag,
                        "posts": posts if posts else "N/A",
                        "views": "N/A",
                        "likes": "N/A",
                        "comments": "N/A",
                        "reactions": "N/A",
                        "category": category,
                        "caption": caption if caption else None,
                        "title": title if title else hashtag,
                        "post_format": post_format,  # Critical for TikTok virality analysis
                        "sound_name": sound_name,  # Critical for content suggestion - trending sounds drive virality
                        "sound_artist": sound_artist,  # Critical for content suggestion
                        "sound_id": sound_id,  # Critical for content suggestion
                        "original_sound": original_sound,  # Critical for virality analysis
                        "language": language,
                        "language_confidence": language_confidence,
                        "engagement_score": engagement,
                        "sentiment_polarity": polarity,
                        "sentiment_label": sentiment
                    })
                except Exception as e:
                    metrics.increment("hashtag_parse_errors_total")
                    if debug:
                        log_error(e, context={"element_index": i+1, "hashtag": hashtag}, logger=logger)
                    continue

            metrics.set_gauge("scrape_hashtags_scraped", float(len(scraped_data)))
            log_with_trace(logging.INFO, f"Scraped {len(scraped_data)} unique hashtags",
                          hashtags_count=len(scraped_data))
            
            # Record proxy success if using proxy pool
            if proxy_used and _global_proxy_pool:
                try:
                    response_time = 0.0  # Could track actual response time
                    _global_proxy_pool.record_success(proxy_used, response_time=response_time)
                except:
                    pass
            
            await context.close()
            return scraped_data, page_source
            
        except Exception as inner_e:
            # Inner try block error (navigation/page load)
            log_error(inner_e, context={"url": url, "stage": "navigation"}, logger=logger)
            try:
                await context.close()
            except:
                pass
            if span:
                span.__exit__(type(inner_e), inner_e, None)
            return [], ""
        
    except Exception as e:
        # Log error with taxonomy
        error_info = log_error(e, context={"url": url, "use_proxy": use_proxy, "debug": debug}, logger=logger)
        metrics.increment("scrape_attempts_failed_total", labels={"use_proxy": str(use_proxy)})
        
        # Record proxy failure if using proxy pool
        if proxy_used and _global_proxy_pool:
            try:
                error_category = error_info.category.value if hasattr(error_info, 'category') else "unknown"
                _global_proxy_pool.record_failure(proxy_used, error_category=error_category)
            except:
                pass
        
        try:
            await context.close()
        except:
            pass
        if span:
            span.__exit__(type(e), e, None)
        return [], ""
    
    finally:
        if span:
            span.__exit__(None, None, None)

async def scrape_tiktok_hashtags(headless=True, debug=True, upload_to_db=True, region="en"):
    """Main scraping function with exponential backoff and fresh browser contexts.
    
    Uses exponential backoff strategy with fresh browser context per retry
    to avoid state leakage between attempts. Includes proxy support and URL fallbacks.
    """
    logger.info("="*60)
    logger.info("TIKTOK SCRAPER - Starting")
    logger.info("="*60)
    
    # CRITICAL: Validate proxy requirements before starting
    proxy_valid, proxy_error = validate_proxy_requirements()
    if not proxy_valid:
        logger.error("="*60)
        logger.error("SCRAPER ABORTED - Proxy validation failed")
        logger.error("="*60)
        logger.error(proxy_error)
        logger.error("="*60)
        
        # Emit metrics
        metrics.increment("scraper_aborted_total", labels={"reason": "proxy_validation_failed"})
        
        # Raise exception to prevent scraping without proxy
        raise RuntimeError(f"Proxy validation failed: {proxy_error}")
    
    start_time = time.time()
    
    # Primary URL
    url = f"https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/{region}"
    
    # Determine if we should use proxy
    use_proxy = (PROXY_SERVER is not None) or (_global_proxy_pool is not None)
    
    if use_proxy:
        logger.info(f"Proxy usage: ENABLED (pool available: {_global_proxy_pool is not None})")
    else:
        logger.info("Proxy usage: DISABLED (no proxy configured)")
    
    scraped_data = None
    page_source = None
    last_error = None
    
    # Attach to current trace context if available (set by run_scraper)
    trace_context = get_trace_context()
    
    # Start request tracing
    with trace_request("scrape_tiktok_hashtags"):
        version_id = str(uuid.uuid4())
        
        # Set metrics
        metrics.increment("scrape_requests_total", labels={"region": region})
        metrics.set_gauge("scrape_requests_active", 1.0)
        
        log_with_trace(
            logging.INFO, 
            "Scraper Started",
            region=region,
            headless=headless,
            debug=debug,
            upload_to_db=upload_to_db,
            version_id=version_id,
            max_retries=MAX_RETRIES,
            max_view_more_clicks=MAX_VIEW_MORE_CLICKS
        )
        
        # Emit scraper metadata
        metrics.set_gauge("scraper_max_retries", float(MAX_RETRIES))
        metrics.set_gauge("scraper_max_view_more_clicks", float(MAX_VIEW_MORE_CLICKS))
        
        # Prepare URLs to try
        urls_to_try = [url.format(region=region) for url in ALTERNATE_URLS]
        
        scraped_data = []
        last_error = None
        
        supabase = None
        if upload_to_db:
            supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)

    async with async_playwright() as p:
        # Launch with additional args for better stealth
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-extensions',
                '--disable-gpu',
                '--enable-features=NetworkService',
                '--ignore-certificate-errors',
                '--allow-running-insecure-content',
            ]
        )
        
        # Exponential backoff retry logic
        for attempt in range(1, MAX_RETRIES + 1):
            attempt_start = time.time()
            try:
                # Create a child span per attempt if we have a trace context
                span_cm = trace_context.create_span(f"scrape_attempt_{attempt + 1}") if trace_context else nullcontext()
                with span_cm:
                    log_with_trace(logging.INFO, f"Scrape attempt {attempt + 1}/{MAX_RETRIES}",
                                  attempt=attempt + 1, max_retries=MAX_RETRIES)
                    
                    # Rotate through URLs on each attempt
                    url_index = attempt % len(urls_to_try)
                    current_url = urls_to_try[url_index]
                    log_with_trace(logging.INFO, f"Trying URL {url_index + 1}/{len(urls_to_try)}",
                                  url=current_url, url_index=url_index)
                    
                    # Use proxy if configured (always try proxy if available, not just on retries)
                    # Ideally we want rotation on every run or fallback
                    use_proxy = (PROXY_SERVER is not None) or (_global_proxy_pool is not None)
                    
                    data, page_source = await scrape_single_attempt(browser, current_url, debug=debug, use_proxy=use_proxy)
                    
                    attempt_duration = (time.time() - attempt_start) * 1000
                    metrics.observe_histogram("scrape_attempt_duration_ms", attempt_duration,
                                            labels={"attempt": str(attempt + 1), "use_proxy": str(use_proxy)})
                    
                    if data and len(data) >= MIN_HASHTAGS_THRESHOLD:  # Success threshold
                        scraped_data = data
                        metrics.increment("scrape_attempts_success_total")
                        metrics.set_gauge("scrape_hashtags_scraped", float(len(scraped_data)))
                        log_with_trace(logging.INFO, f"Successfully scraped {len(scraped_data)} hashtags",
                                      hashtags_count=len(scraped_data), attempt=attempt + 1)
                        break
                    else:
                        metrics.increment("scrape_attempts_insufficient_data_total")
                        log_with_trace(logging.WARNING, f"Attempt {attempt + 1} yielded insufficient data",
                                      hashtags_count=len(data) if data else 0, attempt=attempt + 1)
                        
                        # If this is not the last attempt, wait with exponential backoff
                        if attempt < MAX_RETRIES - 1:
                            backoff_time = BASE_BACKOFF_SEC * (2 ** attempt) + random.uniform(0, 1)
                            log_with_trace(logging.INFO, f"Waiting before retry",
                                          backoff_seconds=backoff_time, attempt=attempt + 1)
                            await asyncio.sleep(backoff_time)
                    
            except Exception as e:
                last_error = e
                attempt_duration = (time.time() - attempt_start) * 1000
                metrics.observe_histogram("scrape_attempt_duration_ms", attempt_duration,
                                        labels={"attempt": str(attempt + 1), "failed": "true"})
                log_error(e, context={"attempt": attempt + 1, "max_retries": MAX_RETRIES}, logger=logger)
                
                if attempt < MAX_RETRIES - 1:
                    backoff_time = BASE_BACKOFF_SEC * (2 ** attempt) + random.uniform(0, 1)
                    log_with_trace(logging.INFO, f"Waiting before retry after error",
                                  backoff_seconds=backoff_time, attempt=attempt + 1)
                    await asyncio.sleep(backoff_time)
        
        await browser.close()
        
        # Upload if we have data (top 10 only)
        if upload_to_db and supabase and scraped_data:
            upload_start = time.time()
            # Use a child span if we have an active trace context
            upload_span_cm = trace_context.create_span("upload_to_database") if trace_context else nullcontext()
            with upload_span_cm:
                log_with_trace(logging.INFO, "Uploading top 10 hashtags to Supabase",
                              hashtags_count=len(scraped_data), top_n=TOP_N_UPLOAD_THRESHOLD)
                # Use asyncio.to_thread to run sync upload in a separate thread
                success = await asyncio.to_thread(
                    upload_to_supabase, 
                    supabase=supabase, 
                    hashtag_data=scraped_data, 
                    table_name="tiktok", 
                    version_id=version_id, 
                    top_n=TOP_N_UPLOAD_THRESHOLD, 
                    local_cache=local_cache
                )
                upload_duration = (time.time() - upload_start) * 1000
                metrics.observe_histogram("database_upload_duration_ms", upload_duration)
                
                if success:
                    metrics.increment("database_uploads_success_total")
                    metrics.set_gauge("database_hashtags_uploaded", float(min(TOP_N_UPLOAD_THRESHOLD, len(scraped_data))))
                    log_with_trace(logging.INFO, "Upload successful",
                                  uploaded_count=min(TOP_N_UPLOAD_THRESHOLD, len(scraped_data)), duration_ms=upload_duration)
                else:
                    metrics.increment("database_uploads_failed_total")
                    log_with_trace(logging.ERROR, "Upload failed")
        
        metrics.set_gauge("scrape_requests_active", 0.0)
        
        if not scraped_data and last_error:
            raise last_error
        
        return scraped_data

async def run_scraper(platform: str = "TikTok", region: str = "en", headless: bool = True, debug: bool = True, upload_to_db: bool = True):
    """Main entry point with run-level metadata emission.
    
    Args:
        platform: Platform name (default: TikTok)
        region: Region code for scraping (default: en)
        headless: Run browser in headless mode
        debug: Enable debug mode with HTML output
        upload_to_db: Upload results to database
    
    Returns:
        List of scraped hashtag data
    """
    start_time = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())
    
    # Start request tracing
    with trace_request("run_scraper", request_id=run_id) as trace:
        # Emit run-level metadata
        run_metadata = {
            "run_id": run_id,
            "platform": platform,
            "region": region,
            "started_at": start_time.isoformat(),
            "headless": headless,
            "debug": debug,
            "upload_to_db": upload_to_db,
            "max_retries": MAX_RETRIES,
            "max_view_more_clicks": MAX_VIEW_MORE_CLICKS
        }
        
        log_with_trace(logging.INFO, "Scraper Started",
                      **run_metadata)
        
        metrics.increment("scraper_runs_total", labels={"platform": platform, "region": region})
        
        # Insert run history record (status: running)
        run_history_id = None
        try:
            supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
            if supabase:
                run_history_record = {
                    "platform": platform,
                    "job_id": run_id,
                    "status": "running",
                    "started_at": start_time.isoformat(),
                    "metadata": {
                        "region": region,
                        "headless": headless,
                        "debug": debug,
                        "upload_to_db": upload_to_db
                    }
                }
                result = await asyncio.to_thread(lambda: supabase.table("run_history").insert(run_history_record).execute())
                if result.data and len(result.data) > 0:
                    run_history_id = result.data[0].get("id")
                    logger.info(f"Run history created: id={run_history_id}")
        except Exception as e:
            logger.warning(f"Failed to create run history record: {e}")
    
        # Initialize Supabase client
        supabase = None
        job_queue = None  # NEW: Job queue for async retries
        
        if upload_to_db:
            supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
            if not supabase:
                logger.warning("Supabase client initialization failed. Data will not be uploaded.")
                metrics.increment("supabase_init_failed_total")
            else:
                logger.info("✅ Supabase client initialized successfully")
                
                # NEW: Initialize job queue for async retries
                if JOB_QUEUE_AVAILABLE:
                    try:
                        job_queue = JobQueue(supabase)
                        logger.info("✅ Job queue initialized for async retries")
                        metrics.increment("job_queue_init_success_total")
                    except Exception as e:
                        logger.warning(f"Failed to initialize job queue: {e}")
                        metrics.increment("job_queue_init_failed_total")
                else:
                    logger.info("Job queue not available (JobQueue module not imported)")
        
        # Run the scraper
        scraped_data = await scrape_tiktok_hashtags(
            headless=headless,
            debug=debug,
            upload_to_db=False,  # We'll handle upload separately
            region=region
        )
        
        # Upload to database if enabled
        if upload_to_db and supabase and scraped_data:
            upload_start = time.time()
            # Use a child span if we have an active trace context
            trace_ctx = get_trace_context()
            upload_span_cm = trace_ctx.create_span("upload_to_database") if trace_ctx else nullcontext()
            with upload_span_cm:
                log_with_trace(logging.INFO, "Uploading top 10 hashtags to Supabase",
                              hashtags_count=len(scraped_data), top_n=TOP_N_UPLOAD_THRESHOLD)
                # Use asyncio.to_thread to run sync upload in a separate thread
                success = await asyncio.to_thread(
                    upload_to_supabase, 
                    supabase=supabase, 
                    hashtag_data=scraped_data, 
                    table_name="tiktok", 
                    version_id=run_id, 
                    top_n=TOP_N_UPLOAD_THRESHOLD, 
                    local_cache=local_cache,
                    job_queue=job_queue # Pass job_queue for async retries
                )
                upload_duration = (time.time() - upload_start) * 1000
                metrics.observe_histogram("database_upload_duration_ms", upload_duration)
                
                if success:
                    metrics.increment("database_uploads_success_total")
                    metrics.set_gauge("database_hashtags_uploaded", float(min(TOP_N_UPLOAD_THRESHOLD, len(scraped_data))))
                    log_with_trace(logging.INFO, "Upload successful",
                                  uploaded_count=min(TOP_N_UPLOAD_THRESHOLD, len(scraped_data)), duration_ms=upload_duration)
                else:
                    metrics.increment("database_uploads_failed_total")
                    log_with_trace(logging.ERROR, "Upload failed")
        

        try:
            results = scraped_data # Use the results from the separate scrape call
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            duration_ms = duration * 1000
            
            # Emit completion metadata
            completion_metadata = {
                "run_id": run_id,
                "finished_at": end_time.isoformat(),
                "duration_seconds": duration,
                "duration_ms": duration_ms,
                "total_hashtags": len(results),
                "status": "success"
            }
            
            metrics.increment("scraper_runs_success_total", labels={"platform": platform, "region": region})
            metrics.observe_histogram("scraper_run_duration_seconds", duration,
                                    labels={"platform": platform, "region": region})
            metrics.set_gauge("scraper_last_run_duration_seconds", duration)
            
            log_with_trace(logging.INFO, "Scraper Success",
                          **completion_metadata)
            
            if results:
                log_with_trace(logging.INFO, "Sample results",
                              sample_count=min(5, len(results)),
                              results=[{"hashtag": item['hashtag'], "posts": item['posts'], 
                                       "score": item['engagement_score']} 
                                      for item in results[:5]])
            
            # Update run history (status: completed)
            if run_history_id:
                try:
                    supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
                    if supabase:
                        update_data = {
                            "status": "completed",
                            "ended_at": end_time.isoformat(),
                            "duration_seconds": duration,
                            "records_scraped": len(results) if results else 0,
                            "records_uploaded": len(results) if results and upload_to_db else 0
                        }
                        await asyncio.to_thread(lambda: supabase.table("run_history").update(update_data).eq("id", run_history_id).execute())
                        logger.info(f"Run history updated: id={run_history_id}, status=completed")
                except Exception as e:
                    logger.warning(f"Failed to update run history: {e}")
            
            return results
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            error_metadata = {
                "run_id": run_id,
                "finished_at": end_time.isoformat(),
                "duration_seconds": duration,
                "status": "failed"
            }
            
            metrics.increment("scraper_runs_failed_total", labels={"platform": platform, "region": region})
            log_with_trace(logging.ERROR, "Scraper Failed", reason=str(e), **error_metadata)
            log_error(e, context=error_metadata, logger=logger)
            
            # Update run history (status: failed)
            if run_history_id:
                try:
                    import traceback
                    supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
                    if supabase:
                        update_data = {
                            "status": "failed",
                            "ended_at": end_time.isoformat(),
                            "duration_seconds": duration,
                            "error_message": str(e),
                            "error_traceback": traceback.format_exc()
                        }
                        await asyncio.to_thread(lambda: supabase.table("run_history").update(update_data).eq("id", run_history_id).execute())
                        logger.info(f"Run history updated: id={run_history_id}, status=failed")
                except Exception as update_error:
                    logger.warning(f"Failed to update run history: {update_error}")
            
            # Check if running in worker context (to prevent recursive loops)
            # If OS_SCRAPER_WORKER is true, it means the worker called us. 
            # If the worker called us and we failed, the worker should handle the retry logic (backoff),
            # so we shoild NOT enqueue a new job here.
            is_worker_context = os.environ.get("OS_SCRAPER_WORKER", "").lower() == "true"
            
            # Add to retry queue IF AVAILABLE and NOT IN WORKER CONTEXT
            if JOB_QUEUE_AVAILABLE and not is_worker_context:
                try:
                    supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
                    if supabase:
                        job_queue = JobQueue(supabase)
                        job_id = await asyncio.to_thread(job_queue.add_job, 
                            job_type="scraper",
                            payload={
                                "platform": platform,
                                "region": region,
                                "headless": headless,
                                "debug": debug,
                                "upload_to_db": upload_to_db,
                                "error": str(e),
                                "run_id": run_id
                            },
                            max_attempts=3
                        )
                        logger.info(f"Failed scrape added to retry queue: job_id={job_id}")
                except Exception as queue_error:
                    logger.warning(f"Failed to add job to retry queue: {queue_error}")
            
            raise


def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of all collected metrics.
    
    Returns:
        Dictionary with metrics summary in Prometheus-style format
    """
    try:
        all_metrics = metrics.get_all_metrics()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": all_metrics
        }
    except:
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "metrics": {}}


def print_metrics_summary():
    """Print metrics summary to console."""
    try:
        summary = get_metrics_summary()
        print("\n" + "="*60)
        print("METRICS SUMMARY")
        print("="*60)
        print(json.dumps(summary, indent=2, default=str))
        print("="*60 + "\n")
    except:
        pass


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='TikTok Hashtag Scraper')
    parser.add_argument('--platform', type=str, default='TikTok', help='Platform to scrape (default: TikTok)')
    parser.add_argument('--region', type=str, default='en', help='Region code (default: en)')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless', help='Run in visible mode')
    parser.add_argument('--debug', action='store_true', default=False, help='Enable debug mode (default: False)')
    parser.add_argument('--no-debug', action='store_false', dest='debug', help='Disable debug mode')
    parser.add_argument('--upload', action='store_true', default=True, help='Upload to database (default: True)')
    parser.add_argument('--no-upload', action='store_false', dest='upload', help='Disable database upload')
    
    # Parse arguments
    args = parser.parse_args()

    print("="*60)
    print(f"{args.platform} Scraper - Starting...")
    print(f"Region: {args.region}, Headless: {args.headless}, Upload: {args.upload}")
    print("="*60)
    
    try:
        results = asyncio.run(run_scraper(
            platform=args.platform,
            region=args.region,
            headless=args.headless,
            debug=args.debug,
            upload_to_db=args.upload
        ))
        
        print("\n" + "="*60)
        print("SCRAPER COMPLETED")
        print("="*60)
        if results:
            print(f"[SUCCESS] Successfully scraped {len(results)} hashtags")
            print(f"\nTop 5 hashtags:")
            for i, item in enumerate(results[:5], 1):
                hashtag = item.get('hashtag', 'N/A') if isinstance(item, dict) else getattr(item, 'topic', 'N/A')
                score = item.get('engagement_score', 0) if isinstance(item, dict) else getattr(item, 'score', 0)
                posts = item.get('posts', 'N/A') if isinstance(item, dict) else getattr(item, 'metrics', {}).get('posts', 'N/A')
                print(f"  {i}. {hashtag} - Score: {score} - Posts: {posts}")
        else:
            print("[WARN]  No hashtags were scraped")
        print("="*60 + "\n")
    except Exception as e:
        print("\n" + "="*60)
        print("SCRAPER FAILED")
        print("="*60)
        print(f"[ERROR] Error: {e}")
        print("="*60 + "\n")
        sys.exit(1)
    finally:
        # Print metrics summary on exit
        try:
            if USE_JSON_LOGGING:
                print_metrics_summary()
        except:
            pass