"""
LinkedIn Trending Hashtags Scraper with Playwright and Rotating Proxies
Scrapes LinkedIn posts to find the top 10 trending hashtags
Uses Playwright for better performance and proxy rotation to avoid blocking
"""

import sys
import io

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
import time
import re
import random
from collections import Counter
import json
from typing import List, Dict, Optional, Tuple
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from uuid import uuid4
from datetime import datetime
from textblob import TextBlob
from langdetect import detect, detect_langs, LangDetectException
from logger import logger

# Load environment variables from .env file
load_dotenv()

from utils.proxies import ProxyRotator
from utils.analysis import (
    analyze_sentiment_multi_method,
    detect_language,
    get_primary_language as get_primary_lang_util
)
class LinkedInHashtagScraper:
    """LinkedIn hashtag scraper using Playwright with proxy support"""
    
    def __init__(self, headless: bool = False, use_proxies: bool = True, 
                 proxy_file: str = "proxies.txt", rotate_proxy_every: int = 10,
                 use_supabase: bool = True, locale: str = None, timezone_id: str = None,
                 geolocation: Dict = None):
        """
        Initialize the scraper
        
        Args:
            headless: Run browser in headless mode
            use_proxies: Whether to use proxy rotation
            proxy_file: Path to proxy file
            rotate_proxy_every: Rotate proxy after N scrolls
            use_supabase: Whether to save data to Supabase
            locale: Browser locale (e.g., 'en-US', 'en-GB', 'fr-FR'). Defaults to env var or 'en-US'
            timezone_id: Timezone ID (e.g., 'America/New_York', 'Europe/London'). Defaults to env var or 'America/New_York'
            geolocation: Dict with 'latitude' and 'longitude' keys. Defaults to env vars or New York coordinates
        """
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.hashtags = []
        self.hashtag_contexts = {}  # Store hashtag -> list of post texts for better sentiment analysis
        self.hashtag_languages = {}  # Store hashtag -> list of detected languages from post contexts
        self.hashtag_captions = {}  # Store hashtag -> list of captions/titles from posts
        self.hashtag_sentiments = {}  # Store hashtag -> list of sentiment scores from multiple methods
        self.headless = headless
        self.use_proxies = use_proxies
        self.rotate_proxy_every = rotate_proxy_every
        self.scroll_count = 0
        self.use_supabase = use_supabase
        self.version_id = str(uuid4())  # Unique version ID for this scraping session
        
        # Performance tracking
        self.start_time = None
        self.posts_processed = 0
        self.hashtags_per_minute = 0
        self.last_progress_save = 0
        
        # Supabase scrape log tracking
        self.scrape_log_id = None  # Track the scrape log entry ID
        
        # Improved duplicate detection using better hashing
        self.seen_post_hashes = set()  # More efficient than string IDs
        
        # Load locale, timezone, and geolocation from environment or use defaults
        self.locale = locale or os.getenv('BROWSER_LOCALE', 'en-US')
        self.timezone_id = timezone_id or os.getenv('BROWSER_TIMEZONE', 'America/New_York')
        
        if geolocation:
            self.geolocation = geolocation
        else:
            lat = os.getenv('BROWSER_LATITUDE')
            lon = os.getenv('BROWSER_LONGITUDE')
            if lat and lon:
                self.geolocation = {"latitude": float(lat), "longitude": float(lon)}
            else:
                # Default to New York coordinates
                self.geolocation = {"latitude": 40.7128, "longitude": -74.0060}
        
        # Initialize Supabase client if enabled
        self.supabase: Optional[Client] = None
        if use_supabase:
            self.init_supabase()
        
        if use_proxies:
            self.proxy_rotator = ProxyRotator(proxy_file)
        else:
            self.proxy_rotator = None
        
        self.current_proxy_server = None  # Track currently active proxy server

    def run_with_retry(self, func, *args, max_retries=3, **kwargs):
        """Execute a function with retry logic and proxy rotation on bot detection or failure"""
        for attempt in range(max_retries):
            # Proactive check: If a network block was detected asynchronously, trigger rotation
            if getattr(self, 'last_network_block', None):
                logger.critical(f"Asynchronous network block detected before {func.__name__}")
                self.handle_linkedin_error() # This will raise RuntimeError and trigger rotation below
                
            try:
                return func(*args, **kwargs)
            except RuntimeError as re:
                # Our bot detection (handle_linkedin_error) raises RuntimeError
                if "Bot detection" in str(re) or "Proxy enforcement" in str(re):
                    logger.critical(f"BOT BLOCK ENCOUNTERED in {func.__name__}: {re}")
                    if attempt < max_retries - 1:
                        logger.info("Retrying with new proxy...")
                        self.rotate_proxy_specifically() # Dedicated method for forced rotation
                    else:
                        raise re
                else:
                    raise re
            except Exception as e:
                logger.error(f"Error in {func.__name__} (attempt {attempt+1}/{max_retries}): {e}")
                
                if self.use_proxies and self.proxy_rotator:
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempting proxy rotation due to general error in {func.__name__}")
                        self.rotate_proxy_specifically()
                
                if attempt == max_retries - 1:
                    logger.error(f"Max retries reached for {func.__name__}")
                    raise e
                
                time.sleep(random.uniform(2, 5))

    def rotate_proxy_specifically(self):
        """Force immediate proxy rotation and browser restart"""
        if not self.use_proxies or not self.proxy_rotator:
            return
            
        try:
            # Mark current proxy as failed if it exists
            if self.current_proxy_server:
                self.proxy_rotator.mark_proxy_failed(self.current_proxy_server)
            
            # Close current browser context
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
                
            # Get new proxy and restart
            new_proxy = self.proxy_rotator.get_proxy_config()
            if new_proxy:
                logger.info(f"Rotating to new proxy: {new_proxy.get('server')}")
                self.setup_browser(new_proxy)
                # If we were logged in, we might need to login again or rely on cookies
                # For this implementation, we'll assume the caller (run_with_retry) might need to re-login if needed
            else:
                logger.error("No more proxies available for rotation")
        except Exception as e:
            logger.error(f"Critical error during forced proxy rotation: {e}")
    
    def init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found in environment variables.")
                self.use_supabase = False
                return
            
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase: {e}")
            self.supabase = None
    
    def log_scrape_start(self):
        """Log scrape start to Supabase scrape_logs table"""
        if not self.use_supabase or not self.supabase:
            return
        
        try:
            from config import PLATFORM_NAME, SUPABASE_LOGS_TABLE, STATUS_RUNNING
            
            log_entry = {
                "platform": PLATFORM_NAME,
                "started_at": datetime.utcnow().isoformat(),
                "status": STATUS_RUNNING,
                "proxy_used": self.current_proxy_server if hasattr(self, 'current_proxy_server') else None,
                "version_id": self.version_id,
                "metadata": {
                    "headless": self.headless,
                    "use_proxies": self.use_proxies
                }
            }
            
            response = self.supabase.table(SUPABASE_LOGS_TABLE).insert(log_entry).execute()
            if hasattr(response, 'data') and response.data and len(response.data) > 0:
                self.scrape_log_id = response.data[0].get('id')
                logger.info(f"Scrape run logged to Supabase (log_id: {self.scrape_log_id})")
        except Exception as e:
            error_msg = str(e)
            if "PGRST205" in error_msg or "scrape_logs" in error_msg:
                logger.error("MISSING TABLE: The 'scrape_logs' table does not exist in your Supabase database.")
                logger.info("FIX: Run the 'unified_trends_schema.sql' script in your Supabase SQL Editor.")
            else:
                logger.warning(f"Failed to log scrape start to Supabase: {e}")
    
    def log_scrape_end(self, status="success", error=None, records_inserted=0):
        """Log scrape end to Supabase scrape_logs table"""
        if not self.use_supabase or not self.supabase or not self.scrape_log_id:
            return
        
        try:
            from config import SUPABASE_LOGS_TABLE
            
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            
            update_data = {
                "ended_at": datetime.utcnow().isoformat(),
                "status": status,
                "error": error,
                "records_inserted": records_inserted,
                "metadata": {
                    "headless": self.headless,
                    "use_proxies": self.use_proxies,
                    "scrolls_performed": getattr(self, 'scroll_count', 0),
                    "posts_processed": getattr(self, 'posts_processed', 0),
                    "total_hashtags": len(self.hashtags) if hasattr(self, 'hashtags') else 0,
                    "unique_hashtags": len(set(self.hashtags)) if hasattr(self, 'hashtags') else 0,
                    "duration_seconds": round(elapsed_time, 2),
                    "hashtags_per_minute": round(self.hashtags_per_minute, 2) if hasattr(self, 'hashtags_per_minute') else 0
                }
            }
            
            # Add proxy stats if available
            if hasattr(self, 'proxy_rotator') and self.proxy_rotator:
                update_data["metadata"]["failed_proxies_count"] = len(self.proxy_rotator.failed_proxies)
                update_data["metadata"]["total_proxies_count"] = len(self.proxy_rotator.proxies)
            
            self.supabase.table(SUPABASE_LOGS_TABLE).update(update_data).eq("id", self.scrape_log_id).execute()
            logger.info(f"Scrape run completed and logged (log_id: {self.scrape_log_id}, status: {status})")
        except Exception as e:
            logger.warning(f"Failed to log scrape end to Supabase: {e}")
    
    def get_user_agent(self) -> str:
        """Get a random user agent to avoid detection"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        return random.choice(user_agents)
    
    def setup_browser(self, proxy: Optional[Dict] = None):
        """Setup Playwright browser with anti-detection measures"""
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
        
        launch_options = {
            "headless": self.headless,
            "args": browser_args,
        }
        
        if proxy:
            launch_options["proxy"] = proxy
            self.current_proxy_server = proxy.get('server')
            logger.info(f"Using proxy: {self.current_proxy_server}")
        else:
            self.current_proxy_server = None
        
        self.browser = self.playwright.chromium.launch(**launch_options)
        
        # Create context with additional stealth settings
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": self.get_user_agent(),
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "permissions": ["geolocation"],
            "geolocation": self.geolocation,
            "color_scheme": "light",
        }
        
        if proxy:
            context_options["proxy"] = proxy
        
        self.context = self.browser.new_context(**context_options)
        
        # Add stealth scripts to avoid detection
        locale_short = self.locale.split('-')[0] if '-' in self.locale else self.locale
        stealth_script = f"""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined
            }});
            
            // Override chrome object
            window.chrome = {{
                runtime: {{}}
            }};
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({{ state: Notification.permission }}) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {{
                get: () => [1, 2, 3, 4, 5]
            }});
            
            // Override languages to match locale
            Object.defineProperty(navigator, 'languages', {{
                get: () => ['{self.locale}', '{locale_short}']
            }});
        """
        self.context.add_init_script(stealth_script)
        
        self.page = self.context.new_page()
        
        # Set extra HTTP headers with locale-aware Accept-Language
        locale_short = self.locale.split('-')[0] if '-' in self.locale else self.locale
        accept_language = f"{self.locale},{locale_short};q=0.9"
        
        self.page.set_extra_http_headers({
            "Accept-Language": accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        # Add network monitoring for bot detection (403/429)
        def handle_response(response):
            try:
                if response.status in [403, 429]:
                    url = response.url
                    if "linkedin.com" in url:
                        logger.critical(f"NETWORK BLOCK DETECTED: HTTP {response.status} on {url}")
                        # Store detection state for main loops to act upon
                        self.last_network_block = {
                            "status": response.status,
                            "url": url,
                            "timestamp": time.time()
                        }
            except Exception:
                pass
                
        self.page.on("response", handle_response)
        self.last_network_block = None
    
    def rotate_proxy_if_needed(self):
        """Rotate proxy if needed based on scroll count"""
        if not self.use_proxies or not self.proxy_rotator:
            return
        
        if self.scroll_count > 0 and self.scroll_count % self.rotate_proxy_every == 0:
            logger.info(f"Rotating proxy after {self.scroll_count} scrolls...")
            new_proxy = self.proxy_rotator.get_proxy_config()
            if new_proxy:
                # Close current context robustly before setting up a new one
                if self.context:
                    try:
                        self.context.close()
                    except Exception as close_error:
                        logger.warning(f"Error closing old context during proxy rotation: {close_error}")
                
                try:
                    logger.info(f"Rotating to new proxy: {new_proxy.get('server')}")
                    self.setup_browser(new_proxy)
                    logger.info("Proxy rotated successfully")
                except Exception as e:
                    logger.error(f"Error rotating proxy: {e}")
                    # Mark this proxy as failed if it was a connection error
                    if new_proxy and 'server' in new_proxy:
                         logger.warning(f"Marking proxy {new_proxy['server']} as failed due to rotation error")
                         self.proxy_rotator.mark_proxy_failed(new_proxy['server'])
                         self.current_proxy_server = None
                    # Continue with current proxy (or try again, but avoiding recursion depth issues)
    
    def start(self):
        """Start Playwright"""
        logger.info("Run Started", context={"start_time": datetime.utcnow().isoformat()})
        
        # Log scrape start to Supabase
        self.log_scrape_start()
        
        self.playwright = sync_playwright().start()
        
        # Initial proxy setup
        proxy = None
        if self.use_proxies and self.proxy_rotator:
            # Try to find a working proxy
            if not self.proxy_rotator.proxy or not self.proxy_rotator.proxies:
                 logger.error("COMPLIANCE FAILURE: No proxies found in 'proxies.txt'.")
                 logger.info("TIP: To run without proxies for testing, set 'USE_PROXIES=false' in your .env file.")
                 raise RuntimeError("Proxy enforcement active: No proxies found in proxy file. Scraper aborted to prevent non-proxy leaks.")

            for _ in range(3): # Try up to 3 times to launch
                proxy = self.proxy_rotator.get_proxy_config()
                if not proxy:
                    continue

                try:
                    self.setup_browser(proxy)
                    return # Successfully started
                except Exception as e:
                    logger.error(f"Failed to launch browser with proxy {proxy.get('server') if proxy else 'None'}: {e}")
                    if proxy and 'server' in proxy:
                         self.proxy_rotator.mark_proxy_failed(proxy['server'])
            
            # If all retries failed, raise an error to enforce proxy usage
            logger.error("COMPLIANCE FAILURE: Failed to initialize any working proxy. Scraper cannot continue safely without proxy enforcement.")
            raise RuntimeError("Proxy enforcement active: No working proxies available. Scraper aborted to prevent non-proxy leaks.")
        else:
            self.setup_browser(None)
    
    def check_for_linkedin_error(self) -> Dict[str, Any]:
        """
        Check if LinkedIn is showing an error page, checkpoint, or bot detection state.
        Returns a dict with 'detected' (bool) and 'type' (str: 'generic', 'block', 'captcha').
        """
        result = {"detected": False, "type": None, "original_text": None}
        try:
            current_url = self.page.url.lower()
            page_text = self.page.inner_text("body").lower()
            
            # 1. URL-based Block Detection
            url_blocks = ["checkpoint", "captcha", "security-check", "real-user-challenge", "access-denied"]
            for pattern in url_blocks:
                if pattern in current_url:
                    result.update({"detected": True, "type": "block", "original_text": f"URL pattern: {pattern}"})
                    return result
            
            # 2. Severe Block/Bot Patterns (Immediate rotation required)
            block_indicators = [
                "unusual activity",
                "security verification",
                "access denied",
                "verify your identity",
                "challenge",
                "security check",
                "automated access",
                "ip has been flagged"
            ]
            for indicator in block_indicators:
                if indicator in page_text:
                    result.update({"detected": True, "type": "block", "original_text": indicator})
                    return result
            
            # 3. Captcha Specifics
            if "captcha" in page_text or "recaptcha" in page_text or self.page.query_selector("iframe[src*='captcha']"):
                result.update({"detected": True, "type": "captcha", "original_text": "captcha detected"})
                return result

            # 4. Generic Error Indicators (Refresh may solve)
            error_indicators = [
                "something went wrong",
                "try again",
                "refresh the page",
                "we're sorry",
                "unable to load",
                "error occurred",
                "temporarily unavailable"
            ]
            for indicator in error_indicators:
                if indicator in page_text:
                    result.update({"detected": True, "type": "generic", "original_text": indicator})
                    return result
            
            return result
        except Exception as e:
            logger.debug(f"Error checking for LinkedIn error page: {e}")
            return result
    
    def handle_linkedin_error(self, max_retries=3) -> bool:
        """Handle LinkedIn error pages by refreshing or rotating proxy if blocked"""
        error_info = self.check_for_linkedin_error()
        
        if not error_info["detected"]:
            return True
        
        error_type = error_info["type"]
        error_text = error_info["original_text"]
        
        # If it's a hard block or captcha, immediate rotation is better than refresh
        if error_type in ["block", "captcha"]:
            logger.critical(f"BOT DETECTION TRIGGERED: {error_text.upper() if error_text else 'UNKNOWN BLOCK'}")
            
            # Mark current proxy as failed if we are using proxies
            if self.use_proxies and self.proxy_rotator:
                current_proxy = getattr(self, 'current_proxy_server', None)
                if current_proxy:
                    logger.warning(f"Marking proxy as failed due to bot detection: {current_proxy}")
                    self.proxy_rotator.mark_proxy_failed(current_proxy)
            
            logger.info("Triggering immediate proxy rotation and browser restart...")
            # We'll allow the higher level loop (start, run_with_retry) to handle the restart 
            # by raising a specific exception or returning False
            raise RuntimeError(f"Bot detection block encountered: {error_text}")

        # For generic errors, try refreshing
        for attempt in range(max_retries):
            logger.warning(f"LinkedIn generic error detected ('{error_text}'). Attempting to refresh (attempt {attempt + 1}/{max_retries})...")
            try:
                # Try clicking "Try again" button if it exists
                try_again_button = self.page.query_selector("button:has-text('Try again'), button:has-text('Refresh')")
                if try_again_button:
                    try_again_button.click()
                    time.sleep(random.uniform(3, 5))
                else:
                    self.page.reload(wait_until="networkidle")
                    time.sleep(random.uniform(3, 5))
                
                # Check if error is gone
                new_error_info = self.check_for_linkedin_error()
                if not new_error_info["detected"]:
                    logger.info("Error page resolved after refresh")
                    return True
                
                # If it's now a block after refresh, rotate
                if new_error_info["type"] in ["block", "captcha"]:
                    raise RuntimeError(f"Generic error escalated to block: {new_error_info['original_text']}")
                    
            except RuntimeError:
                raise # Re-raise runtime error for block handling
            except Exception as e:
                logger.warning(f"Error during refresh: {e}")
                try:
                    self.page.reload(wait_until="networkidle")
                    time.sleep(random.uniform(3, 5))
                except Exception:
                    pass
        
        logger.error("Could not resolve LinkedIn error page after multiple attempts")
        return False
    
    def is_logged_in(self) -> bool:
        """Check if user is logged into LinkedIn"""
        try:
            current_url = self.page.url.lower()
            page_title = self.page.title().lower()
            
            # Strong indicators that we're NOT logged in
            if "login" in current_url or "login" in page_title or "sign-in" in current_url:
                return False
            
            # Wait a moment for page to load
            time.sleep(1)
            
            # Check for multiple logged-in indicators (need at least 2 to be sure)
            logged_in_count = 0
            
            # Check 1: Navigation elements
            try:
                nav_selectors = [
                    "nav[role='navigation']",
                    "nav.global-nav",
                    "nav[class*='nav']",
                    "header[role='banner']"
                ]
                for selector in nav_selectors:
                    if self.page.query_selector(selector):
                        logged_in_count += 1
                        break
            except Exception:
                pass
            
            # Check 2: Search bar or user menu
            try:
                search_selectors = [
                    "input[placeholder*='Search']",
                    "input[aria-label*='Search']",
                    "button[aria-label*='Me']",
                    "img[alt*='profile']"
                ]
                for selector in search_selectors:
                    if self.page.query_selector(selector):
                        logged_in_count += 1
                        break
            except Exception:
                pass
            
            # Check 3: Feed-specific elements
            try:
                feed_selectors = [
                    "main[role='main']",
                    "div[data-test-id='feed-container']",
                    "div.feed-container",
                    "section.feed"
                ]
                for selector in feed_selectors:
                    if self.page.query_selector(selector):
                        logged_in_count += 1
                        break
            except Exception:
                pass
            
            # Check 4: URL-based check
            if "feed" in current_url and "login" not in current_url:
                logged_in_count += 1
            
            # Need at least 2 indicators to be confident
            return logged_in_count >= 2
            
        except Exception as e:
            # If check fails, assume not logged in to be safe
            return False
    
    def login(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Navigate to LinkedIn login page and verify login
        Note: For security, manual login is recommended
        """
        logger.info("Navigating to LinkedIn login...")
        try:
            self.page.goto("https://www.linkedin.com/login", wait_until="networkidle", timeout=30000)
            time.sleep(random.uniform(2, 4))  # Random delay to appear more human
            
            # Check for error page
            if self.check_for_linkedin_error():
                logger.warning("Error page detected on login page. Attempting to resolve...")
                if not self.handle_linkedin_error():
                    logger.error("Could not resolve error. Please check the browser window manually.")
                    return
        except Exception as e:
            logger.warning(f"Error navigating to login page: {e}")
            logger.info("Trying to continue...")
        
        if email and password:
            try:
                email_input = self.page.wait_for_selector("#username", timeout=10000)
                password_input = self.page.wait_for_selector("#password", timeout=10000)
                
                # Type with human-like delays
                email_input.type(email, delay=random.uniform(50, 150))
                time.sleep(random.uniform(0.5, 1.5))
                password_input.type(password, delay=random.uniform(50, 150))
                time.sleep(random.uniform(0.5, 1.5))
                
                login_button = self.page.wait_for_selector('button[type="submit"]', timeout=5000)
                login_button.click()
                
                time.sleep(5)
                logger.info("Login attempt completed. Verifying login status...")
            except Exception as e:
                logger.warning(f"Error during automated login: {e}")
                logger.info("Please login manually in the browser window.")
        else:
            logger.info("Please login manually in the browser window.")
            input("Press Enter after you have logged in...")
        
        # Don't verify here - let the feed navigation handle it
        # This avoids double navigation and timeout issues
        logger.info("Login process initiated. Login status will be verified when accessing feed.")
        return True
    
    def extract_hashtags_from_text(self, text: str) -> List[str]:
        """Extract hashtags from text using regex, filtering out low-quality ones"""
        hashtag_pattern = r'#[\w]+'
        hashtags = re.findall(hashtag_pattern, text)
        
        # Filter out low-quality hashtags with improved criteria
        filtered_hashtags = []
        seen_in_text = set()  # Avoid duplicates in same text
        
        for tag in hashtags:
            tag_lower = tag.lower()
            # Remove the # for validation
            tag_content = tag_lower[1:] if tag_lower.startswith('#') else tag_lower
            
            # Skip if already seen in this text
            if tag_lower in seen_in_text:
                continue
            
            # Enhanced filter criteria:
            # 1. Must be at least 2 characters (excluding #)
            # 2. Not just numbers
            # 3. Contains at least one letter (not just numbers/symbols)
            # 4. Not common stop words
            # 5. Not too long (likely spam)
            stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                         'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should'}
            
            if (len(tag_content) >= 2 and 
                len(tag_content) <= 50 and  # Max length to avoid spam
                not tag_content.isdigit() and 
                any(c.isalpha() for c in tag_content) and  # Must contain at least one letter
                tag_content not in stop_words):
                filtered_hashtags.append(tag_lower)
                seen_in_text.add(tag_lower)
        
        return filtered_hashtags
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """Detect language using external utility"""
        return detect_language(text)
    
    def get_primary_language(self, hashtag: str) -> Tuple[str, float]:
        """Get primary language using external utility"""
        if hashtag not in self.hashtag_languages or not self.hashtag_languages[hashtag]:
            return ('unknown', 0.0)
        return get_primary_lang_util(self.hashtag_languages[hashtag])
    
    def extract_caption_from_linkedin_post(self, post_element, post_text: str) -> str:
        """
        Extract caption/title from LinkedIn post element.
        LinkedIn posts often have the main content in specific selectors.
        
        Args:
            post_element: Playwright element for the post
            post_text: Full text from the post
            
        Returns:
            Extracted caption text
        """
        try:
            # Try to find the main content area in LinkedIn posts
            caption_selectors = [
                "div.feed-shared-text",
                "div.feed-shared-text__text-view",
                "div.update-components-text",
                "span.feed-shared-text__text-view",
                "div[data-test-id='feed-shared-text']",
                ".feed-shared-update-v2__description",
                ".feed-shared-update-v2__commentary"
            ]
            
            for selector in caption_selectors:
                try:
                    caption_elem = post_element.query_selector(selector)
                    if caption_elem:
                        caption_text = caption_elem.inner_text().strip()
                        if caption_text and len(caption_text) > 10:
                            return caption_text[:500]  # Limit to 500 chars
                except Exception as e:
                    logger.debug(f"Failed to extract caption with selector {selector}: {e}")
                    continue
            
            # Fallback: Extract from full text by taking first meaningful lines
            lines = post_text.split('\n')
            caption_lines = []
            for line in lines[:5]:  # First 5 lines usually contain the main content
                line = line.strip()
                # Skip common metadata lines
                if line and len(line) > 3 and not any(skip in line.lower() for skip in [
                    'liked by', 'comment', 'share', 'repost', 'follow', 'see more', 'see less'
                ]):
                    caption_lines.append(line)
                    if sum(len(l) for l in caption_lines) >= 300:
                        break
            
            caption = ' '.join(caption_lines).strip()
            return caption[:500] if caption else post_text[:300]
        except Exception as e:
            # Fallback to first part of post text
            return post_text[:300] if post_text else ""
    
    def store_hashtag_with_sentiment(self, hashtag: str, post_text: str, caption: str = None, 
                                     analyze_sentiment: bool = True):
        """
        Store hashtag with context, caption, language, and multi-method sentiment analysis
        
        Args:
            hashtag: The hashtag found in the post
            post_text: The full post text
            caption: Optional caption/title (if None, will use post_text)
            analyze_sentiment: Whether to perform sentiment analysis
        """
        # Initialize structures if needed
        if hashtag not in self.hashtag_contexts:
            self.hashtag_contexts[hashtag] = []
        if hashtag not in self.hashtag_languages:
            self.hashtag_languages[hashtag] = []
        if hashtag not in self.hashtag_captions:
            self.hashtag_captions[hashtag] = []
        if hashtag not in self.hashtag_sentiments:
            self.hashtag_sentiments[hashtag] = []
        
        # Store post text context
        context_snippet = post_text[:200] if len(post_text) > 200 else post_text
        self.hashtag_contexts[hashtag].append(context_snippet)
        
        # Store caption
        if caption:
            self.hashtag_captions[hashtag].append(caption)
        elif post_text:
            # Extract caption from post text
            caption = self.extract_caption_from_linkedin_post(None, post_text)
            if caption:
                self.hashtag_captions[hashtag].append(caption)
        
        # Detect and store language
        detected_lang, _ = self.detect_language(post_text)
        if detected_lang != 'unknown':
            self.hashtag_languages[hashtag].append(detected_lang)
        
        # Perform multi-method sentiment analysis using external utility
        if analyze_sentiment:
            sentiment_text = caption if caption else post_text[:500]
            sentiment_results = analyze_sentiment_multi_method(sentiment_text)
            self.hashtag_sentiments[hashtag].append(sentiment_results)
    
    def get_aggregated_sentiment(self, hashtag: str) -> Dict:
        """Get aggregated sentiment scores for a hashtag across all occurrences"""
        if hashtag not in self.hashtag_sentiments or not self.hashtag_sentiments[hashtag]:
            return {
                'textblob': {'polarity': 0.0, 'label': 'neutral'},
                'vader': {'compound': 0.0, 'label': 'neutral'},
                'transformer': {'score': 0.0, 'label': 'neutral'},
                'consensus_label': 'neutral',
                'average_score': 0.0
            }
        
        sentiments = self.hashtag_sentiments[hashtag]
        
        # Aggregate scores
        textblob_scores = [s.get('textblob', {}).get('polarity', 0.0) for s in sentiments]
        vader_scores = [s.get('vader', {}).get('compound', 0.0) for s in sentiments]
        transformer_scores = [s.get('transformer', {}).get('score', 0.0) for s in sentiments]
        
        # Count labels
        textblob_labels = [s.get('textblob', {}).get('label', 'neutral') for s in sentiments]
        vader_labels = [s.get('vader', {}).get('label', 'neutral') for s in sentiments]
        transformer_labels = [s.get('transformer', {}).get('label', 'neutral') for s in sentiments]
        
        # Calculate averages
        avg_textblob = sum(textblob_scores) / len(textblob_scores) if textblob_scores else 0.0
        avg_vader = sum(vader_scores) / len(vader_scores) if vader_scores else 0.0
        avg_transformer = sum(transformer_scores) / len(transformer_scores) if transformer_scores else 0.0
        
        # Get most common labels
        most_common_textblob = Counter(textblob_labels).most_common(1)[0][0] if textblob_labels else 'neutral'
        most_common_vader = Counter(vader_labels).most_common(1)[0][0] if vader_labels else 'neutral'
        most_common_transformer = Counter(transformer_labels).most_common(1)[0][0] if transformer_labels else 'neutral'
        
        # Overall consensus
        all_labels = textblob_labels + vader_labels + transformer_labels
        consensus_label = Counter(all_labels).most_common(1)[0][0] if all_labels else 'neutral'
        
        # Overall average
        all_scores = textblob_scores + vader_scores + transformer_scores
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        return {
            'textblob': {'polarity': round(avg_textblob, 3), 'label': most_common_textblob},
            'vader': {'compound': round(avg_vader, 3), 'label': most_common_vader},
            'transformer': {'score': round(avg_transformer, 3), 'label': most_common_transformer},
            'consensus_label': consensus_label,
            'average_score': round(average_score, 3),
            'sample_count': len(sentiments)
        }
    
    def analyze_sentiment_multi_method(self, text: str) -> Dict:
        """Analyze sentiment using external utility"""
        return analyze_sentiment_multi_method(text)
    
    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """
        Analyze sentiment of text using TextBlob (backward compatibility)
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (polarity, label) where:
            - polarity: float between -1 (negative) and 1 (positive)
            - label: 'positive', 'negative', or 'neutral'
        """
        return self.analyze_sentiment_textblob(text)
    
    def wait_for_loading(self, timeout=5):
        """Wait for LinkedIn loading indicators to disappear"""
        try:
            # Wait for common loading spinners to disappear
            loading_selectors = [
                ".feed-loading-spinner",
                ".loading-spinner",
                "[data-test-id='loading-spinner']",
                ".artdeco-loader"
            ]
            for selector in loading_selectors:
                try:
                    self.page.wait_for_selector(selector, state="hidden", timeout=1000)
                except Exception:
                    pass
        except Exception:
            pass
    
    def try_click_show_more(self):
        """Try to find and click 'Show more' or similar buttons to load more content"""
        # Only try clicking "Show more" every 3 scrolls to avoid spam
        if not hasattr(self, '_last_show_more_click'):
            self._last_show_more_click = -5
        
        if self.scroll_count - self._last_show_more_click < 3:
            return False
        
        try:
            # Common LinkedIn "show more" button selectors
            show_more_selectors = [
                "button[aria-label*='Show more']",
                "button[aria-label*='See more']",
                "button:has-text('Show more')",
                "button:has-text('See more posts')",
                ".feed-show-more-button",
                "button.feed-show-more"
            ]
            
            for selector in show_more_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        print("   🔘 Found 'Show more' button, clicking...")
                        button.click()
                        
                        # Wait longer after clicking and check for errors
                        print("   ⏳ Waiting for content to load after clicking 'Show more'...")
                        time.sleep(random.uniform(5, 8))  # Wait longer
                        
                        # Check for error page after clicking
                        if self.check_for_linkedin_error():
                            print("   ⚠️  Error page appeared after clicking 'Show more'. Attempting to resolve...")
                            if not self.handle_linkedin_error():
                                print("   ❌ Could not resolve error. Continuing anyway...")
                        
                        # Wait for loading indicators
                        self.wait_for_loading(timeout=8)
                        
                        # Scroll after clicking to trigger more loading
                        try:
                            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(random.uniform(2, 3))
                        except Exception as e:
                            print(f"   ⚠️  Error scrolling after 'Show more': {e}")
                        
                        self._last_show_more_click = self.scroll_count
                        print("   ✅ 'Show more' button clicked and page loaded")
                        return True
                except Exception:
                    # Continue trying other selectors
                    continue
        except Exception as e:
            logger.debug(f"Error trying to click 'Show more': {e}")
        return False
    
    def interact_with_posts(self, posts):
        """Interact with posts to trigger LinkedIn to load more content"""
        try:
            # Hover over a few random posts to simulate engagement
            if posts and len(posts) > 0:
                # Select 1-2 random posts to hover over
                posts_to_interact = random.sample(posts, min(2, len(posts)))
                for post in posts_to_interact:
                    try:
                        # Hover over the post
                        post.hover()
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        # Sometimes scroll the post into view more
                        post.scroll_into_view_if_needed()
                        time.sleep(random.uniform(0.3, 0.6))
                    except Exception:
                        continue
        except Exception:
            pass
    
    def human_like_scroll(self, aggressive=False):
        """Perform human-like scrolling with multiple techniques to trigger loading"""
        if aggressive:
            # More aggressive scrolling when we're not getting new posts
            logger.info("Performing aggressive scroll to trigger loading...")
            
            # Scroll way past the bottom multiple times
            for i in range(5):
                scroll_height = self.page.evaluate("document.body.scrollHeight")
                current_scroll = self.page.evaluate("window.pageYOffset || window.scrollY")
                # Scroll past the bottom
                self.page.evaluate(f"window.scrollTo(0, {scroll_height + 1000})")
                time.sleep(random.uniform(0.5, 1.0))
                self.page.keyboard.press("End")
                time.sleep(random.uniform(0.5, 1.0))
                self.wait_for_loading(timeout=2)
            
            # Scroll back up a bit then down again
            self.page.evaluate("window.scrollBy(0, -500)")
            time.sleep(random.uniform(0.5, 1.0))
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(random.uniform(1.0, 1.5))
        else:
            # Normal scrolling
            # Optimized scrolling for speed - reduced wait times
            # Method 1: Quick incremental scrolling
            for _ in range(2):  # Reduced from 3 to 2
                scroll_increment = random.randint(400, 700)
                self.page.evaluate(f"window.scrollBy(0, {scroll_increment})")
                time.sleep(random.uniform(0.3, 0.6))  # Reduced from 0.5-1.0
                
                # Wait for any loading indicators (shorter timeout)
                self.wait_for_loading(timeout=1)
            
            # Method 2: Scroll to near bottom (90%) to trigger loading
            scroll_height = self.page.evaluate("document.body.scrollHeight")
            target_scroll = int(scroll_height * 0.9)
            self.page.evaluate(f"window.scrollTo(0, {target_scroll})")
            time.sleep(random.uniform(0.5, 0.8))  # Reduced from 1.0-1.5
            self.wait_for_loading(timeout=1)
            
            # Method 3: Scroll to absolute bottom
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(random.uniform(0.5, 0.8))  # Reduced from 1.0-1.5
            self.wait_for_loading(timeout=1)
            
            # Method 4: Use keyboard End key
            self.page.keyboard.press("End")
            time.sleep(random.uniform(0.4, 0.7))  # Reduced from 0.8-1.2
            self.wait_for_loading(timeout=1)
    
    def scrape_public_hashtags(self, hashtag: str = None):
        """
        Attempt to scrape hashtags from public LinkedIn pages (very limited)
        Note: LinkedIn heavily restricts public access. This method has limited success.
        
        Args:
            hashtag: Optional specific hashtag to search for
        """
        logger.info("Attempting to scrape public content (limited access)...")
        logger.warning("Note: LinkedIn requires login for most content. Public scraping is very limited.")
        
        hashtags_found = []
        
        # Try to access public company pages or posts
        public_urls = [
            "https://www.linkedin.com/company/linkedin/posts/",
            "https://www.linkedin.com/pulse/",
        ]
        
        for url in public_urls:
            try:
                logger.info(f"   Trying: {url}")
                self.page.goto(url, wait_until="networkidle", timeout=15000)
                time.sleep(3)
                
                # Check if we got redirected to login
                if "login" in self.page.url.lower():
                    logger.warning(f"Redirected to login page. Public access not available.")
                    continue
                
                # Try to extract hashtags from visible content
                page_text = self.page.inner_text("body")
                found_hashtags = self.extract_hashtags_from_text(page_text)
                if found_hashtags:
                    hashtags_found.extend(found_hashtags)
                    logger.info(f"Found {len(found_hashtags)} hashtags from {url}")
                
            except Exception as e:
                logger.warning(f"Error accessing {url}: {e}")
                continue
        
        if hashtags_found:
            self.hashtags.extend(hashtags_found)
            logger.info(f"Total hashtags found from public pages: {len(hashtags_found)}")
        else:
            logger.warning("No hashtags found from public pages. Login is required for LinkedIn feed access.")
        
        return len(hashtags_found) > 0
    
    def scroll_and_collect_hashtags(self, scroll_pause_time: float = 2, max_scrolls: int = 50, require_login: bool = True):
        """
        Scroll through LinkedIn feed and collect hashtags
        
        Args:
            scroll_pause_time: Base time to wait between scrolls
            max_scrolls: Maximum number of scrolls to perform
            require_login: If True, requires login. If False, tries public scraping first (limited)
        """
        self.start_time = time.time()
        logger.info(f"Starting scraper at {datetime.now().strftime('%H:%M:%S')}")
        # If login not required, try public scraping first
        if not require_login:
            logger.info("Attempting public scraping (no login required)...")
            if self.scrape_public_hashtags():
                logger.info("Found some hashtags from public pages!")
                # Continue to try feed as well
            else:
                logger.warning("Public scraping failed. Login is required for LinkedIn feed.")
                if not self.is_logged_in():
                    logger.info("Attempting to access feed anyway...")
        
        logger.info("Navigating to LinkedIn feed...")
        try:
            # Navigate to feed
            self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(3, 5))  # Wait for page to load
            
            # Check current URL to see if we got redirected
            current_url = self.page.url.lower()
            
            # Verify we're logged in
            logged_in = self.is_logged_in()
            
            if not logged_in:
                if require_login:
                    # Check if we're on login page
                    if "login" in current_url or "challenge" in current_url:
                        print("⚠️  Not logged in! You are on the login page.")
                        print("   Please log in manually in the browser window.")
                        print("   The scraper will wait for you to complete login...")
                        
                        # Wait for user to login - check periodically
                        max_wait_attempts = 30  # Wait up to 5 minutes
                        for wait_attempt in range(max_wait_attempts):
                            time.sleep(10)  # Check every 10 seconds
                            try:
                                # Try navigating to feed again
                                self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                                time.sleep(2)
                                
                                if self.is_logged_in():
                                    print("✅ Login detected! Continuing...")
                                    logged_in = True
                                    break
                                else:
                                    current_url = self.page.url.lower()
                                    if "login" not in current_url and "challenge" not in current_url:
                                        # Not on login page, might be loading
                                        if wait_attempt % 2 == 0:  # Print every 20 seconds
                                            print(f"   ⏳ Page loading... checking login status ({wait_attempt * 10}s elapsed)")
                                    else:
                                        if wait_attempt % 3 == 0:  # Print every 30 seconds
                                            print(f"   ⏳ Still waiting for login... ({wait_attempt * 10}s elapsed)")
                            except Exception as e:
                                if wait_attempt % 3 == 0:
                                    print(f"   ⏳ Checking login status... ({wait_attempt * 10}s elapsed)")
                        
                        if not logged_in:
                            print("❌ Login timeout. Cannot proceed without login.")
                            print("   LinkedIn requires login to access the feed.")
                            return
                    else:
                        # Not on login page but login check failed - might be loading
                        print("⚠️  Login status unclear. Waiting a bit more for page to load...")
                        time.sleep(5)
                        if not self.is_logged_in():
                            print("❌ Still not logged in. Please ensure you are logged in.")
                            return
                else:
                    print("⚠️  Not logged in and public scraping didn't work.")
                    print("   LinkedIn requires login to access the feed.")
                    return
            
            # Check for error page immediately after loading
            if self.check_for_linkedin_error():
                logger.warning("Error page detected on feed. Attempting to resolve...")
                if not self.handle_linkedin_error():
                    logger.error("Could not resolve error page. Please check the browser window.")
                    logger.info("You may need to manually refresh or wait a few minutes.")
                    return
        except Exception as e:
            logger.error(f"Error navigating to feed: {e}")
            logger.info("Attempting to handle error...")
            if not self.handle_linkedin_error():
                logger.error("Could not resolve error. Stopping.")
                return
        
        # Optimized initial scroll for faster startup
        print("🔄 Performing initial scroll to load posts...")
        # Scroll down quickly in increments
        for i in range(2):  # Reduced from 3
            scroll_pos = (i + 1) * 600
            self.page.evaluate(f"window.scrollTo(0, {scroll_pos})")
            time.sleep(random.uniform(0.8, 1.2))  # Reduced from 1.5-2.5
            self.wait_for_loading(timeout=2)  # Reduced from 3
        
        # Scroll to bottom
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(2, 3))  # Reduced from 4-6
        self.wait_for_loading(timeout=3)  # Reduced from 5
        
        # Scroll back to top
        self.page.evaluate("window.scrollTo(0, 0)")
        time.sleep(random.uniform(1, 1.5))  # Reduced from 2-3
        
        print(f"🚀 Starting to scroll and collect hashtags (max {max_scrolls} scrolls)...")
        
        last_height = self.page.evaluate("document.body.scrollHeight")
        last_post_count = 0
        scroll_count = 0
        no_change_count = 0  # Track consecutive times with no height change
        no_new_posts_count = 0  # Track consecutive times with no new posts
        seen_post_ids = set()  # Track seen posts to avoid duplicates (backward compatibility)
        self.posts_scanned = 0  # Track total posts scanned for statistics
        posts = []  # Initialize posts variable
        
        # Initialize improved duplicate detection
        if not hasattr(self, 'seen_post_hashes'):
            self.seen_post_hashes = set()
        
            # Check for bot detection / network blocks
            if getattr(self, 'last_network_block', None):
                logger.critical("Network block detected by async listener. Initiating recovery...")
                self.handle_linkedin_error() # This will raise RuntimeError for blocks
                
            # Check for LinkedIn error pages periodically
            if scroll_count % 5 == 0:  # Check every 5 scrolls
                self.handle_linkedin_error() # Now raises RuntimeError on blocks
            
            # Rotate proxy if needed
            self.rotate_proxy_if_needed()
            
            # Extract hashtags from visible posts
            posts = []  # Reset posts for each iteration
            try:
                # Optimized wait times for faster scraping
                time.sleep(random.uniform(1.2, 2.0))  # Further optimized for speed
                # Wait for loading indicators to disappear (shorter timeout)
                self.wait_for_loading(timeout=2)  # Further optimized
                
                # Find all post containers - LinkedIn uses various selectors
                # Try multiple selectors as LinkedIn changes their structure frequently
                post_selectors = [
                    "div.feed-shared-update-v2",
                    "article.feed-shared-update-v2",
                    "div[data-id*='urn:li:activity']",
                    "div.occludable-update",
                    "div.feed-shared-update-v2__description",
                    "div[data-urn*='activity']",
                    "article[data-id]",
                    "div.update-components-actor",
                    "section.feed-update-v2",
                    "div[data-test-id='feed-shared-update-v2']",
                    "div.feed-shared-update-v2__content",
                    "article[data-urn]",
                    "div.feed-shared-update-v2__description-wrapper",
                    "div.update-components-text",
                    "div.feed-shared-update-v2__commentary",
                    # Generic fallbacks
                    "article",
                    "div[class*='feed']",
                    "div[class*='update']"
                ]
                
                posts = []
                for selector in post_selectors:
                    try:
                        posts = self.page.query_selector_all(selector)
                        if posts and len(posts) > 0:
                            # Filter out very small elements that are likely not posts
                            posts = [p for p in posts if p.bounding_box() and p.bounding_box()['height'] > 50]
                            if posts and len(posts) > 0:
                                logger.debug(f"Using selector: {selector} (found {len(posts)} posts)")
                            break
                    except Exception:
                        continue
                
                # If still no posts, try getting all visible text containers
                if not posts or len(posts) == 0:
                    try:
                        # Try a more generic approach - look for any divs with substantial text
                        all_divs = self.page.query_selector_all("div")
                        posts = []
                        for div in all_divs:
                            try:
                                text = div.inner_text()
                                # Check if it looks like a post (has substantial text and might have hashtags)
                                if text and len(text) > 100 and ('#' in text or 'like' in text.lower() or 'comment' in text.lower()):
                                    bbox = div.bounding_box()
                                    if bbox and bbox['height'] > 100:  # Must be substantial height
                                        posts.append(div)
                                        if len(posts) >= 20:  # Limit to avoid too many false positives
                                            break
                            except Exception:
                                continue
                        if posts:
                            logger.debug(f"Using generic text-based detection (found {len(posts)} potential posts)")
                    except Exception:
                        pass
                
                # If no posts found with selectors, check what's happening
                if not posts or len(posts) == 0:
                    # Check if we're still on the feed page
                    current_url = self.page.url
                    if "feed" not in current_url.lower():
                        print(f"⚠️  Not on feed page anymore. Current URL: {current_url}")
                        print("   🔄 Navigating back to feed...")
                        self.page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
                        time.sleep(random.uniform(3, 5))
                        continue
                    
                    # Check for LinkedIn blocking/error messages
                    page_text = self.page.inner_text("body").lower()
                    if any(keyword in page_text for keyword in ["unusual activity", "verify", "security check", "temporarily restricted"]):
                        print("⚠️  LinkedIn may be showing a security check. Please check the browser window.")
                        time.sleep(random.uniform(5, 8))
                        continue
                    
                    # Debug: Show page title and some page content for first few scrolls
                    if scroll_count < 3:
                        try:
                            page_title = self.page.title()
                            logger.debug(f"Debug: Page title: {page_title}")
                            # Check if we're logged in by looking for common LinkedIn elements
                            has_nav = self.page.query_selector("nav") is not None
                            has_feed = "feed" in current_url.lower()
                            logger.debug(f"Debug: Has nav: {has_nav}, On feed page: {has_feed}")
                        except Exception:
                            pass
                    
                    # Only show warning every 5 scrolls to reduce spam
                    if scroll_count % 5 == 0:
                        print(f"⚠️  No posts found (scroll {scroll_count}). Trying to extract from page text...")
                    
                    # Try extracting from page text as fallback
                    try:
                        page_text_full = self.page.inner_text("body")
                        hashtags = self.extract_hashtags_from_text(page_text_full)
                        if hashtags:
                            # Avoid duplicates by checking against seen hashtags
                            new_hashtags = [h for h in hashtags if h not in self.hashtags]
                            if new_hashtags and scroll_count % 5 == 0:
                                self.hashtags.extend(new_hashtags)
                                logger.info(f"Extracted {len(new_hashtags)} hashtags from page text")
                    except Exception:
                        pass
                    
                    # If no posts found multiple times, try refreshing
                    if scroll_count > 5 and no_new_posts_count > 3:
                        print("🔄 No posts found for multiple scrolls. Refreshing page...")
                        self.page.reload(wait_until="networkidle")
                        time.sleep(random.uniform(5, 7))
                        no_new_posts_count = 0
                    
                    # Still try to scroll even if no posts found - LinkedIn may need scrolling to load content
                    # Don't continue here, let the scrolling logic run below
                
                # Also extract from entire page text periodically to catch any we might have missed
                if scroll_count % 10 == 0:  # Every 10 scrolls, also check page text
                    try:
                        page_text = self.page.inner_text("body")
                        page_hashtags = self.extract_hashtags_from_text(page_text)
                        # Add any new hashtags we haven't seen
                        new_page_hashtags = [h for h in page_hashtags if h not in self.hashtags]
                        if new_page_hashtags:
                            self.hashtags.extend(new_page_hashtags)
                            logger.info(f"Found {len(new_page_hashtags)} additional hashtags from page text")
                    except Exception:
                        pass
                
                print(f"📊 Found {len(posts)} posts. Extracting hashtags...")
                
                # Interact with posts to trigger more content loading
                if scroll_count % 2 == 0:  # Interact every other scroll
                    self.interact_with_posts(posts)
                
                # Extract text from each post
                new_posts_count = 0
                posts_with_hashtags = 0
                for post in posts:
                    try:
                        # Get post text first to create a unique identifier
                        post_text = post.inner_text()
                        if not post_text or len(post_text.strip()) < 10:
                            continue  # Skip empty or very short posts
                        
                        # Improved duplicate detection using better hashing
                        post_preview = post_text[:300].strip()
                        # Create a more stable hash using first 100 chars, last 100 chars, and length
                        if len(post_text) > 200:
                            # Use first 100, middle 50, last 100 chars for better uniqueness
                            mid_point = len(post_text) // 2
                            hash_content = post_text[:100] + post_text[mid_point-25:mid_point+25] + post_text[-100:] + str(len(post_text))
                        elif len(post_text) > 100:
                            hash_content = post_text[:50] + post_text[-50:] + str(len(post_text))
                        else:
                            hash_content = post_text
                        
                        # Use hash() for faster comparison
                        post_hash = hash(hash_content)
                        
                        # Check if we've seen this post before (using set for O(1) lookup)
                        if post_hash in self.seen_post_hashes:
                            continue  # Skip already processed posts
                        
                        # Mark as seen
                        self.seen_post_hashes.add(post_hash)
                        seen_post_ids.add(str(post_hash))  # Keep for backward compatibility
                        new_posts_count += 1
                        self.posts_scanned += 1  # Track total posts scanned
                        
                        # Debug: Show when we find a new post
                        if scroll_count <= 5:  # Only show for first few scrolls
                            logger.debug(f"New post found: {post_preview[:60]}...")
                        
                        # Extract caption/title from post (main content, excluding metadata)
                        caption = self.extract_caption_from_linkedin_post(post, post_text)
                        
                        # Extract hashtags from post text
                        hashtags = self.extract_hashtags_from_text(post_text)
                        if hashtags:
                            self.hashtags.extend(hashtags)
                            posts_with_hashtags += 1
                            
                            # Store hashtag with full context, caption, language, and sentiment analysis
                            for hashtag in hashtags:
                                self.store_hashtag_with_sentiment(
                                    hashtag=hashtag,
                                    post_text=post_text,
                                    caption=caption,
                                    analyze_sentiment=True
                                )
                            logger.info(f"Found {len(hashtags)} hashtags in post", context={"preview": post_preview[:50]})
                    except Exception as e:
                        logger.warning(f"Error processing post: {e}")
                        continue
                
                if new_posts_count > 0:
                    self.posts_processed += new_posts_count
                    # Calculate performance metrics
                    elapsed_time = time.time() - self.start_time if self.start_time else 1
                    self.hashtags_per_minute = (len(self.hashtags) / elapsed_time) * 60 if elapsed_time > 0 else 0
                    
                    # Progress indicator
                    progress_pct = (scroll_count / max_scrolls * 100) if max_scrolls > 0 else 0
                    logger.info(f"Processed {new_posts_count} new posts ({posts_with_hashtags} with hashtags). "
                          f"Total: {len(self.hashtags)} hashtags | "
                          f"Progress: {progress_pct:.1f}% | "
                          f"Speed: {self.hashtags_per_minute:.1f} hashtags/min")
                elif scroll_count % 3 == 0:  # Only show duplicate message every 3 scrolls
                    logger.debug(f"All {len(posts)} posts are duplicates (already processed). Total hashtags: {len(self.hashtags)}")
                
                # Track if we got new posts
                if new_posts_count == 0:
                    no_new_posts_count += 1
                else:
                    no_new_posts_count = 0
                    last_post_count = len(posts)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" in error_msg or "target" in error_msg:
                    logger.warning(f"Browser/page was closed during operation. Stopping...")
                    break
                else:
                    logger.warning(f"Error extracting posts: {e}")
                    # Continue trying if it's not a fatal error
            
            # Stop if we've been stuck on the same posts for too long (optimized threshold)
            if no_new_posts_count >= 8 and scroll_count > 8:  # Reduced from 10 for faster completion
                logger.warning(f"No new posts found for {no_new_posts_count} consecutive scrolls.")
                logger.info(f"LinkedIn may not be loading more content. Stopping to avoid infinite loop.")
                unique_posts = len(self.seen_post_hashes) if hasattr(self, 'seen_post_hashes') else len(seen_post_ids)
                logger.info(f"Collected {len(self.hashtags)} hashtags from {unique_posts} unique posts.")
                break
            
            # Determine if we should use aggressive scrolling
            use_aggressive = (no_new_posts_count >= 2 and scroll_count > 3)
            
            # Always try to scroll - LinkedIn needs scrolling to load more content
            # Scroll more aggressively if no posts found
            if posts and len(posts) > 0 or scroll_count < 10:
                try:
                    # Human-like scroll with multiple techniques
                    self.human_like_scroll(aggressive=use_aggressive)
                    scroll_count += 1
                    self.scroll_count = scroll_count
                    
                    # Enhanced progress display
                    progress_pct = (scroll_count / max_scrolls * 100) if max_scrolls > 0 else 0
                    elapsed = time.time() - self.start_time if self.start_time else 0
                    estimated_total = (elapsed / scroll_count * max_scrolls) if scroll_count > 0 else 0
                    remaining = max(0, estimated_total - elapsed)
                    
                    logger.info(f"Scroll {scroll_count}/{max_scrolls} ({progress_pct:.1f}%) | "
                          f"Elapsed: {elapsed/60:.1f}m | "
                          f"Est. remaining: {remaining/60:.1f}m | "
                          f"Hashtags: {len(self.hashtags)}")
                    
                    # Try clicking "Show more" buttons if they exist
                    show_more_clicked = self.try_click_show_more()
                    
                    # Optimized wait times for faster scraping
                    wait_time = random.uniform(scroll_pause_time + 1, scroll_pause_time + 2.5)  # Reduced from +3 to +6
                    if show_more_clicked:
                        # Already waited after clicking, but add a bit more
                        wait_time = random.uniform(1, 2)  # Reduced from 2-4
                        if scroll_count % 5 == 0:
                            print(f"   ⏳ Additional wait after 'Show more' click: {wait_time:.1f}s...")
                    elif use_aggressive:
                        wait_time += 1.5  # Reduced from +3
                        if scroll_count % 5 == 0:
                            print(f"⏳ Waiting {wait_time:.1f}s after aggressive scroll...")
                    elif scroll_count % 10 == 0:  # Only print wait time every 10 scrolls
                        print(f"⏳ Waiting {wait_time:.1f}s for content to load...")
                    
                    time.sleep(wait_time)
                    
                    # Wait for any loading indicators
                    self.wait_for_loading(timeout=5)
                    
                    # Check for error page after waiting
                    if self.check_for_linkedin_error():
                        logger.warning("Error page detected after scroll. Attempting to resolve...")
                        if not self.handle_linkedin_error():
                            logger.error("Could not resolve error. Continuing...")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "closed" in error_msg or "target" in error_msg:
                        logger.warning(f"Browser/page was closed during scroll. Stopping...")
                        break
                    elif "navigation" in error_msg or "timeout" in error_msg:
                        logger.warning(f"Navigation/Timeout error: {e}")
                        if self.current_proxy_server and self.proxy_rotator:
                            self.proxy_rotator.mark_proxy_failed(self.current_proxy_server)
                        scroll_count += 1
                        continue
                    else:
                        logger.warning(f"Error during scroll: {e}")
                        scroll_count += 1
                        continue
            else:
                # If no posts found after many scrolls, still try scrolling but more aggressively
                try:
                    logger.info(f"No posts found yet, trying aggressive scroll (scroll {scroll_count + 1})...")
                    self.human_like_scroll(aggressive=True)
                    scroll_count += 1
                    self.scroll_count = scroll_count
                    logger.info(f"Scroll {scroll_count}/{max_scrolls} (no posts found, trying aggressive scroll...)")
                    time.sleep(random.uniform(5, 8))  # Wait longer for content to load
                    self.wait_for_loading(timeout=5)
                except Exception as e:
                    logger.warning(f"Error during aggressive scroll: {e}")
                    scroll_count += 1
                    self.scroll_count = scroll_count
                time.sleep(random.uniform(2, 4))
            
            # Check if we've reached the bottom (give it more tries)
            try:
                new_height = self.page.evaluate("document.body.scrollHeight")
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" in error_msg or "target" in error_msg:
                    print(f"⚠️  Browser/page was closed. Stopping...")
                    break
                else:
                    print(f"⚠️  Error checking page height: {e}")
                    continue
            try:
                current_post_count = len(self.page.query_selector_all("div.feed-shared-update-v2"))
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" in error_msg or "target" in error_msg:
                    logger.warning(f"Browser/page was closed. Stopping...")
                    break
                current_post_count = 0
            
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 5 and no_new_posts_count >= 3:  # More patient - wait longer
                    print("🏁 Reached bottom of page or no more content loading.")
                    break
                else:
                    if scroll_count % 3 == 0:  # Only print every 3 scrolls
                        print(f"⏳ No new content yet (height: {no_change_count}/5, posts: {no_new_posts_count}/3), continuing...")
                    # Try scrolling more aggressively with multiple attempts
                    try:
                        for attempt in range(3):
                            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(random.uniform(1, 2))
                            self.page.keyboard.press("End")
                            time.sleep(random.uniform(1, 2))
                            self.wait_for_loading(timeout=3)
                        # Extra wait after aggressive scrolling
                        time.sleep(random.uniform(3, 5))
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "closed" in error_msg or "target" in error_msg:
                            print(f"⚠️  Browser/page was closed. Stopping...")
                            break
            else:
                no_change_count = 0  # Reset counter if we got new content
            last_height = new_height
        
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        logger.info(f"Finished scrolling!")
        logger.info(f"Final Statistics:")
        logger.info(f"   • Total hashtags collected: {len(self.hashtags)}")
        logger.info(f"   • Unique hashtags: {len(set(self.hashtags))}")
        logger.info(f"   • Posts processed: {self.posts_processed}")
        logger.info(f"   • Scrolls performed: {scroll_count}")
        logger.info(f"   • Time elapsed: {elapsed_time/60:.2f} minutes")
        logger.info(f"   • Average speed: {self.hashtags_per_minute:.1f} hashtags/minute")
        if self.posts_processed > 0:
            logger.info(f"   • Hashtags per post: {len(self.hashtags)/self.posts_processed:.2f}")
    
    def get_top_trending_hashtags(self, top_n: int = 10, min_occurrences: int = 1) -> List[Tuple[str, int]]:
        """
        Get top N trending hashtags with quality filtering
        
        Args:
            top_n: Number of top hashtags to return
            min_occurrences: Minimum number of occurrences to include
            
        Returns:
            List of tuples (hashtag, count) sorted by frequency
        """
        if not self.hashtags:
            return []
        
        hashtag_counter = Counter(self.hashtags)
        
        # Filter hashtags by minimum occurrences and quality
        filtered_hashtags = []
        for hashtag, count in hashtag_counter.items():
            # Skip if below minimum occurrences
            if count < min_occurrences:
                continue
            
            # Additional quality checks
            tag_content = hashtag.replace('#', '').strip()
            
            # Skip if it's just numbers or too short
            if tag_content.isdigit() or len(tag_content) < 2:
                continue
            
            # Skip common non-meaningful patterns
            if tag_content in ['a', 'i', 'the', 'an', 'is', 'are', 'was', 'were']:
                continue
            
            filtered_hashtags.append((hashtag, count))
        
        # Sort by count (descending) and return top N
        filtered_hashtags.sort(key=lambda x: x[1], reverse=True)
        return filtered_hashtags[:top_n]
    
    def save_results(self, filename: str = "trending_hashtags.json", skip_supabase: bool = False):
        """Save results to JSON file and Supabase with enhanced data"""
        top_hashtags = self.get_top_trending_hashtags(10, min_occurrences=1)
        
        total_hashtags = len(self.hashtags)
        unique_hashtags = len(set(self.hashtags))
        
        # Enhanced results structure
        results = {
            "scrape_metadata": {
                "platform": "linkedin",
                "scraped_at": datetime.utcnow().isoformat(),
                "version_id": str(self.version_id),
                "total_posts_scanned": getattr(self, 'posts_scanned', 0),
                "scrolls_performed": getattr(self, 'scroll_count', 0)
            },
            "statistics": {
                "total_hashtags_collected": total_hashtags,
                "unique_hashtags": unique_hashtags,
                "average_occurrences": round(total_hashtags / unique_hashtags, 2) if unique_hashtags > 0 else 0,
                "top_10_percentage": round(sum(count for _, count in top_hashtags) / total_hashtags * 100, 2) if total_hashtags > 0 else 0
            },
            "top_10_trending_hashtags": [
                {
                    "rank": i + 1,
                    "hashtag": tag,
                    "count": count,
                    "percentage": round((count / total_hashtags * 100), 2) if total_hashtags > 0 else 0,
                    "sentiment": self.get_aggregated_sentiment(tag).get('consensus_label', 'neutral'),
                    "sentiment_scores": self.get_aggregated_sentiment(tag),
                    "caption": self.hashtag_captions.get(tag, [None])[0] if tag in self.hashtag_captions and self.hashtag_captions[tag] else None,
                    "language": self.get_primary_language(tag)[0] if tag in self.hashtag_languages else 'unknown',
                    "language_confidence": round(self.get_primary_language(tag)[1], 3) if tag in self.hashtag_languages else 0.0
                }
                for i, (tag, count) in enumerate(top_hashtags)
            ],
            "all_hashtags_summary": {
                "total_unique": unique_hashtags,
                "hashtags_with_context": len([h for h in set(self.hashtags) if h in self.hashtag_contexts])
            }
        }
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
        
        # Save to Supabase and track records inserted
        records_inserted = 0
        if not skip_supabase and self.use_supabase and self.supabase:
            try:
                records_inserted = self.save_to_supabase(top_hashtags)
            except Exception as e:
                logger.error(f"Error saving to Supabase: {e}")
                logger.info("Results saved to JSON file only")
        
        return results, records_inserted
    
    def save_to_supabase(self, top_hashtags: List[Tuple[str, int]]) -> int:
        """Save hashtag data to Supabase database"""
        if not self.supabase:
            return 0
        
        from config import SUPABASE_TRENDS_TABLE
        
        logger.info("Saving data to Supabase...")
        
        # Calculate engagement metrics
        total_hashtags = len(self.hashtags)
        unique_hashtags = len(set(self.hashtags))
        
        # Prepare data for each hashtag
        records_to_insert = []
        
        if not top_hashtags:
            logger.warning("No hashtags to save to Supabase")
            return
        
        for hashtag, count in top_hashtags:
            # Get aggregated sentiment scores from all methods (needed for engagement calculation)
            aggregated_sentiment = self.get_aggregated_sentiment(hashtag)
            sentiment_polarity = aggregated_sentiment.get('average_score', 0.0)
            
            # Calculate IMPROVED engagement score using multiple factors (0-100 scale)
            # Factor 1: Frequency score (0-50 points) - how often it appears relative to all hashtags
            frequency_score = (count / total_hashtags) * 50 if total_hashtags > 0 else 0
            
            # Factor 2: Post diversity score (0-30 points) - how many unique posts contain it
            # More unique posts = better engagement (not just repeated in same post)
            unique_posts_with_hashtag = len(self.hashtag_contexts.get(hashtag, []))
            total_posts_processed = max(getattr(self, 'posts_processed', 1), 1)
            # Calculate what percentage of posts contain this hashtag
            post_coverage = unique_posts_with_hashtag / total_posts_processed
            post_diversity_score = min(30, post_coverage * 30)
            
            # Factor 3: Sentiment boost (0-20 points) - positive sentiment indicates better engagement
            # Normalize sentiment from [-1, 1] to [0, 20]
            # Positive sentiment gets higher boost
            sentiment_boost = ((sentiment_polarity + 1) / 2) * 20
            
            # Calculate total engagement score (0-100 scale)
            engagement_score = frequency_score + post_diversity_score + sentiment_boost
            
            # Ensure it's between 0 and 100
            engagement_score = max(0, min(100, round(engagement_score, 2)))
            
            # Get caption if available
            caption = None
            if hashtag in self.hashtag_captions and self.hashtag_captions[hashtag]:
                caption = self.hashtag_captions[hashtag][0]  # Get first caption
            
            # Detect primary language for hashtag
            primary_lang, lang_confidence = self.get_primary_language(hashtag)
            
            # Extract sentiment scores
            textblob_data = aggregated_sentiment.get('textblob', {})
            vader_data = aggregated_sentiment.get('vader', {})
            transformer_data = aggregated_sentiment.get('transformer', {})
            
            # Backward compatibility: use consensus label for sentiment_label
            sentiment_label = aggregated_sentiment.get('consensus_label', 'neutral')
            # sentiment_polarity already calculated above for engagement score
            
            # Prepare metadata with engagement score breakdown
            metadata = {
                "total_occurrences": count,
                "total_hashtags_collected": total_hashtags,
                "unique_hashtags": unique_hashtags,
                "percentage": round((count / total_hashtags) * 100, 2) if total_hashtags > 0 else 0,
                "scraped_from": "linkedin_feed",
                "session_id": self.version_id,
                "sentiment_analyzed": True,
                "language_detected": primary_lang,
                "language_confidence": round(lang_confidence, 3),
                "sentiment_sample_count": aggregated_sentiment.get('sample_count', 0),
                # Engagement score breakdown for transparency
                "engagement_breakdown": {
                    "frequency_score": round(frequency_score, 2),
                    "post_diversity_score": round(post_diversity_score, 2),
                    "sentiment_boost": round(sentiment_boost, 2),
                    "unique_posts_with_hashtag": unique_posts_with_hashtag,
                    "total_posts_processed": total_posts_processed,
                    "engagement_score_total": round(engagement_score, 2)
                }
            }
            
            # Build record matching User's specific 'linkedin' table schema
            # Schema: id, platform, topic_hashtag, engagement_score, sentiment_polarity, 
            #         sentiment_label, posts, views, metadata, scraped_at, version_id
            
            # Combine all additional data into metadata
            full_metadata = metadata.copy()
            full_metadata.update({
                "sentiment_details": aggregated_sentiment,
                "caption": caption,
                "language": primary_lang,
                "language_confidence": round(lang_confidence, 3),
                "sentiment_textblob": textblob_data,
                "sentiment_vader": vader_data,
                "sentiment_transformer": transformer_data
            })
            
            record = {
                "platform": "linkedin",
                "topic_hashtag": hashtag,
                "engagement_score": round(engagement_score, 2),
                
                # Sentiment
                "sentiment_polarity": sentiment_polarity,
                "sentiment_label": sentiment_label,
                
                # Statistics
                "posts": count,
                "views": None,
                
                # Metadata and tracking
                "metadata": full_metadata,
                "scraped_at": datetime.utcnow().isoformat(),
                "version_id": self.version_id
            }
            
            records_to_insert.append(record)
        
        # Insert records into Supabase (matching Instagram schema structure)
        if not records_to_insert:
            logger.warning("No records generated for insertion")
            return

        # Retry logic for batch insertion
        max_retries = 3
        batch_success = False
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to save {len(records_to_insert)} hashtags to Supabase (Attempt {attempt+1}/{max_retries})...")
                logger.info(f"   Table: {SUPABASE_TRENDS_TABLE} (platform: linkedin)")
                logger.info(f"   Version ID: {self.version_id}")
                
                response = self.supabase.table(SUPABASE_TRENDS_TABLE).insert(records_to_insert).execute()
                
                # Verify the response
                if hasattr(response, 'data') and response.data:
                    saved_count = len(response.data)
                    logger.info(f"Successfully saved {saved_count} hashtags to Supabase")
                    logger.info(f"   Version ID: {self.version_id}")
                    logger.info(f"   Fields saved: engagement_score, sentiment, posts, metadata (with full details)")
                    batch_success = True
                    return saved_count  # Return the count of records inserted
                else:
                    logger.warning(f"Insert completed but no data returned in response")
                    batch_success = True # Assume success if no exception, but warn
                    return len(records_to_insert)  # Return expected count
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Error inserting data to Supabase (Attempt {attempt+1}): {e}")
                
                # Check if it's a schema/column error - suggest updating schema
                if "column" in error_msg.lower() or "schema" in error_msg.lower() or "PGRST204" in error_msg or "PGRST205" in error_msg:
                    logger.warning("Schema mismatch or missing table detected!")
                    logger.warning("Please run the schema from unified_trends_schema.sql")
                    
                    # Try with only required fields as fallback immediately
                    logger.info("Attempting with available fields (minimal schema)...")
                    
                    minimal_records = []
                    for record in records_to_insert:
                        minimal_record = {
                            "platform": record.get("platform", "linkedin"),
                            "topic_hashtag": record.get("topic_hashtag"),
                            "engagement_score": record.get("engagement_score", 0.0),
                            "sentiment_polarity": record.get("sentiment_polarity", 0.0),
                            "sentiment_label": record.get("sentiment_label", "neutral"),
                            "posts": record.get("posts", 0),
                            "metadata": record.get("metadata", {}),
                            "scraped_at": record.get("scraped_at"),
                            "version_id": record.get("version_id")
                        }
                        minimal_records.append(minimal_record)
                    
                    try:
                        self.supabase.table(SUPABASE_TRENDS_TABLE).insert(minimal_records).execute()
                        logger.info(f"Successfully saved {len(minimal_records)} hashtags to Supabase {SUPABASE_TRENDS_TABLE} table (minimal fields)")
                        batch_success = True
                        return len(minimal_records)  # Return count of records inserted
                    except Exception as e2:
                        logger.error(f"Still failed with minimal fields: {e2}")
                        break # Don't retry schema errors
                
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1)) # Backoff
                else:
                    logger.error(f"Failed to insert batch after {max_retries} attempts.")

        if not batch_success:
            # Try inserting one by one if batch fails and not a schema error (or if schema retry failed)
            logger.info("Attempting to insert records one by one...")
            success_count = 0
            for record in records_to_insert:
                try:
                    # Try with full record first
                    self.supabase.table(SUPABASE_TRENDS_TABLE).insert(record).execute()
                    success_count += 1
                except Exception as insert_error:
                    error_str = str(insert_error).lower()
                    if "column" in error_str or "schema" in error_str:
                        # Try minimal fields as fallback
                        try:
                            minimal_record = {
                                "platform": record.get("platform", "linkedin"),
                                "topic_hashtag": record.get("topic_hashtag"),
                                "engagement_score": record.get("engagement_score", 0.0),
                                "sentiment_polarity": record.get("sentiment_polarity", 0.0),
                                "sentiment_label": record.get("sentiment_label", "neutral"),
                                "posts": record.get("posts", 0),
                                "metadata": record.get("metadata", {}),
                                "scraped_at": record.get("scraped_at"),
                                "version_id": record.get("version_id")
                            }
                            self.supabase.table(SUPABASE_TRENDS_TABLE).insert(minimal_record).execute()
                            success_count += 1
                        except Exception:
                            # Dump keys to log for audit on schema mismatch failure
                            if isinstance(record, dict):
                                logger.warning(f"Skipping {record.get('topic_hashtag', 'unknown')}: Schema mismatch. Record keys: {list(record.keys())}")
                            else:
                                logger.warning(f"Skipping {record.get('topic_hashtag', 'unknown')}: Schema mismatch (unknown record type)")
                    else:
                        logger.warning(f"Failed to insert {record.get('topic_hashtag', 'unknown')}: {insert_error}")
            logger.info(f"Inserted {success_count}/{len(records_to_insert)} records")
            return success_count  # Return count of successfully inserted records
        
        return 0  # If we get here, nothing was inserted
            
    def save_dashboard_data(self, output_file="dashboard_data.js", results=None):
        """Save data for the QA dashboard"""
        records_inserted = 0
        if results is None:
            results, records_inserted = self.save_results(filename="trending_hashtags.json", skip_supabase=True)
        
        # Read logs
        logs = []
        try:
            if os.path.exists("scraper_logs.jsonl"):
                with open("scraper_logs.jsonl", "r", encoding="utf-8") as f:
                     # Read last 500 lines to keep file size manageable
                     lines = f.readlines()
                     if len(lines) > 500:
                         lines = lines[-500:]
                     for line in lines:
                          try:
                              logs.append(json.loads(line))
                          except json.JSONDecodeError as json_e:
                              logger.warning(f"Skipping malformed log entry in scraper_logs.jsonl: {json_e}")
        except Exception as e:
            logger.warning(f"Failed to read logs for dashboard: {e}")

        # Add duration and proxy stats to metadata
        if "scrape_metadata" not in results:
             results["scrape_metadata"] = {}
             
        results["scrape_metadata"]["duration_seconds"] = time.time() - self.start_time if self.start_time else 0
        
        # Proxy stats
        if self.proxy_rotator:
             results["scrape_metadata"]["failed_proxies_count"] = len(self.proxy_rotator.failed_proxies)
             results["scrape_metadata"]["total_proxies_count"] = len(self.proxy_rotator.proxies)
        
        results["logs"] = logs
        
        # Write as JS file
        js_content = f"window.DASHBOARD_DATA = {json.dumps(results, indent=2)};"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(js_content)
            logger.info(f"Dashboard data saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save dashboard data: {e}")
    
    def print_results(self):
        """Print top trending hashtags to console with enhanced formatting"""
        top_hashtags = self.get_top_trending_hashtags(10, min_occurrences=1)
        
        if not top_hashtags:
            logger.info("No hashtags found. Try scrolling more or check if posts are loading.")
            return
        
        # Calculate statistics
        total_hashtags = len(self.hashtags)
        unique_hashtags = len(set(self.hashtags))
        total_occurrences = sum(count for _, count in top_hashtags)
        
        logger.info("="*70)
        logger.info("TOP 10 TRENDING HASHTAGS ON LINKEDIN")
        logger.info("="*70)
        
            # Print hashtags with percentage, trend indicator, sentiment, language, and engagement score
        for i, (hashtag, count) in enumerate(top_hashtags, 1):
            percentage = (count / total_hashtags * 100) if total_hashtags > 0 else 0
            # Create a simple bar visualization
            bar_length = int(percentage / 2)  # Scale bar to fit
            bar = "█" * min(bar_length, 30)
            
            # Add trend indicator based on count
            if count >= 5:
                trend = "📈"
            elif count >= 3:
                trend = "📊"
            else:
                trend = "📌"
            
            # Get sentiment analysis (all three methods)
            aggregated_sentiment = self.get_aggregated_sentiment(hashtag)
            textblob_data = aggregated_sentiment.get('textblob', {})
            vader_data = aggregated_sentiment.get('vader', {})
            transformer_data = aggregated_sentiment.get('transformer', {})
            consensus_label = aggregated_sentiment.get('consensus_label', 'neutral')
            
            # Get language detection
            primary_lang, lang_confidence = self.get_primary_language(hashtag)
            lang_display = f"{primary_lang.upper()}" if primary_lang != 'unknown' else "N/A"
            
            # Calculate engagement score for display
            total_hashtags_for_engagement = len(self.hashtags)
            frequency_score = (count / total_hashtags_for_engagement) * 50 if total_hashtags_for_engagement > 0 else 0
            unique_posts_with_hashtag = len(self.hashtag_contexts.get(hashtag, []))
            total_posts_processed = max(getattr(self, 'posts_processed', 1), 1)
            post_coverage = unique_posts_with_hashtag / total_posts_processed
            post_diversity_score = min(30, post_coverage * 30)
            sentiment_polarity = aggregated_sentiment.get('average_score', 0.0)
            sentiment_boost = ((sentiment_polarity + 1) / 2) * 20
            engagement_score = min(100, round(frequency_score + post_diversity_score + sentiment_boost, 2))
            
            # Sentiment emoji
            sentiment_emoji = {
                'positive': '😊',
                'negative': '😞',
                'neutral': '😐'
            }.get(consensus_label, '😐')
            
            logger.info(f"{i:2d}. {hashtag:30s} {trend} {count:3d} times ({percentage:5.1f}%) {bar}")
            logger.info(f"     Sentiment: {sentiment_emoji} {consensus_label.upper():8s} | "
                  f"TextBlob: {textblob_data.get('label', 'N/A'):8s} ({textblob_data.get('polarity', 0.0):+.2f}) | "
                  f"VADER: {vader_data.get('label', 'N/A'):8s} ({vader_data.get('compound', 0.0):+.2f}) | "
                  f"Transformer: {transformer_data.get('label', 'N/A'):8s} ({transformer_data.get('score', 0.0):+.2f})")
            logger.info(f"     Language: {lang_display} (confidence: {lang_confidence:.1%})")
            logger.info(f"     Engagement Score: {engagement_score:.1f}/100 "
                  f"(Frequency: {frequency_score:.1f} | Diversity: {post_diversity_score:.1f} | Sentiment: {sentiment_boost:.1f})")
            print()  # Empty line for readability
        
        logger.info("="*70)
        
        # Enhanced statistics
        logger.info("COLLECTION STATISTICS")
        logger.info(f"   • Total hashtags collected: {total_hashtags}")
        logger.info(f"   • Unique hashtags found: {unique_hashtags}")
        logger.info(f"   • Average occurrences per hashtag: {total_hashtags/unique_hashtags:.2f}" if unique_hashtags > 0 else "   • Average occurrences per hashtag: 0.00")
        logger.info(f"   • Top 10 represent: {total_occurrences/total_hashtags*100:.1f}% of all hashtags" if total_hashtags > 0 else "   • Top 10 represent: 0.0% of all hashtags")
        
        # Sentiment analysis statistics
        if top_hashtags:
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
            languages_detected = {}
            
            for hashtag, _ in top_hashtags:
                aggregated_sentiment = self.get_aggregated_sentiment(hashtag)
                consensus = aggregated_sentiment.get('consensus_label', 'neutral')
                if consensus in sentiment_counts:
                    sentiment_counts[consensus] += 1
                
                lang, _ = self.get_primary_language(hashtag)
                if lang != 'unknown':
                    languages_detected[lang] = languages_detected.get(lang, 0) + 1
            
            logger.info("SENTIMENT ANALYSIS (All 3 Methods)")
            logger.info(f"   • Positive: {sentiment_counts['positive']} hashtags")
            logger.info(f"   • Neutral: {sentiment_counts['neutral']} hashtags")
            logger.info(f"   • Negative: {sentiment_counts['negative']} hashtags")
            
            if languages_detected:
                logger.info("LANGUAGE DETECTION")
                sorted_langs = sorted(languages_detected.items(), key=lambda x: x[1], reverse=True)
                for lang, count in sorted_langs[:5]:  # Top 5 languages
                    lang_name = lang.upper()
                    logger.info(f"   • {lang_name}: {count} hashtag(s)")
        
        # Show hashtag categories if available
        if top_hashtags:
            logger.info("INSIGHTS")
            # Categorize hashtags
            tech_keywords = ['tech', 'coding', 'programming', 'developer', 'software', 'data', 'ai', 'ml', 'python', 'java', 'sql']
            career_keywords = ['career', 'job', 'hiring', 'interview', 'growth', 'professional', 'skills']
            business_keywords = ['business', 'marketing', 'sales', 'leadership', 'entrepreneur', 'startup']
            
            tech_count = sum(1 for h, _ in top_hashtags if any(kw in h.lower() for kw in tech_keywords))
            career_count = sum(1 for h, _ in top_hashtags if any(kw in h.lower() for kw in career_keywords))
            business_count = sum(1 for h, _ in top_hashtags if any(kw in h.lower() for kw in business_keywords))
            
            if tech_count > 0:
                logger.info(f"   • Technology-related: {tech_count} hashtags")
            if career_count > 0:
                logger.info(f"   • Career-related: {career_count} hashtags")
            if business_count > 0:
                logger.info(f"   • Business-related: {business_count} hashtags")
    
    def close(self):
        """Close the browser and Playwright"""
        import sys
        import threading
        
        def cleanup_with_timeout():
            """Cleanup function that can be interrupted"""
            try:
                # Close context first
                if self.context:
                    try:
                        self.context.close()
                    except Exception:
                        pass
                
                # Close browser
                if self.browser:
                    try:
                        self.browser.close()
                    except Exception:
                        pass
                
                # Stop playwright
                if self.playwright:
                    try:
                        self.playwright.stop()
                    except Exception:
                        pass
            except Exception:
                pass
        
        try:
            # Run cleanup in a thread with timeout
            cleanup_thread = threading.Thread(target=cleanup_with_timeout, daemon=True)
            cleanup_thread.start()
            cleanup_thread.join(timeout=3)  # Wait max 3 seconds
            
            if cleanup_thread.is_alive():
                # If cleanup is taking too long, just continue
                logger.info("Browser cleanup initiated (may take a moment)...")
            else:
                logger.info("Browser closed.")
        except KeyboardInterrupt:
            # If user interrupts during cleanup, just exit
            logger.warning("Cleanup interrupted. Results were already saved.")
            sys.exit(0)
        except Exception:
            # Ignore any cleanup errors - results are already saved
            logger.info("Browser cleanup completed.")


def main():
    """Main function to run the scraper"""
    scraper = None
    success = False # Track overall run success
    records_inserted = 0  # Track records inserted to Supabase
    error_message = None  # Track error for logging
    
    try:
        # Read configuration from environment variables
        headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        use_proxies = os.getenv('USE_PROXIES', 'true').lower() == 'true'
        proxy_file = os.getenv('PROXY_FILE', 'proxies.txt')
        rotate_proxy_every = int(os.getenv('ROTATE_PROXY_EVERY', '10'))
        scroll_pause_time = float(os.getenv('SCROLL_PAUSE_TIME', '1.5'))  # Reduced for faster scraping
        max_scrolls = int(os.getenv('MAX_SCROLLS', '50'))  # Reduced default for faster completion
        output_file = os.getenv('OUTPUT_FILE', 'trending_hashtags.json')
        linkedin_email = os.getenv('LINKEDIN_EMAIL', '')
        linkedin_password = os.getenv('LINKEDIN_PASSWORD', '')
        use_supabase = os.getenv('USE_SUPABASE', 'true').lower() == 'true'
        
        # Initialize scraper with environment variables
        scraper = LinkedInHashtagScraper(
            headless=headless,
            use_proxies=use_proxies,
            proxy_file=proxy_file,
            rotate_proxy_every=rotate_proxy_every,
            use_supabase=use_supabase
        )
        
        # Start Playwright once at the beginning
        scraper.start()
        
        # Define the core scraping flow to be wrapped in retry logic
        def perform_scrape():
            # Check login status and login if needed
            if not scraper.is_logged_in():
                if linkedin_email and linkedin_password:
                    logger.info("Proceeding with automated login...")
                    scraper.login(email=linkedin_email, password=linkedin_password)
                else:
                    logger.info("Proceeding with manual login...")
                    scraper.login()  # Manual login
            
            # Scroll and collect hashtags
            scraper.scroll_and_collect_hashtags(
                scroll_pause_time=scroll_pause_time,
                max_scrolls=max_scrolls
            )
        
        # Execute the flow with proxy-aware retry logic
        scraper.run_with_retry(perform_scrape, max_retries=3)
        
        # Print results
        scraper.print_results()
        
        # Save results to file and get records count
        results, records_inserted = scraper.save_results(filename=output_file)
        scraper.save_dashboard_data(results=results)
        
        success = True # specific success marker
        
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user.")
        error_message = "Interrupted by user"
        # Still try to save results if we have any
        if scraper and scraper.hashtags:
            logger.info("Saving partial results...")
            try:
                scraper.print_results()
                results, records_inserted = scraper.save_results(filename=output_file)
                scraper.save_dashboard_data(results=results)
            except Exception:
                pass
        # Log as interrupted
        if scraper:
            scraper.log_scrape_end(status="interrupted", error=error_message, records_inserted=records_inserted)
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        error_message = str(e)
        # Log as failed
        if scraper:
            scraper.log_scrape_end(status="failed", error=error_message, records_inserted=records_inserted)
    finally:
        if scraper:
            try:
                scraper.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        # Log successful completion
        if success and scraper:
            scraper.log_scrape_end(status="success", error=None, records_inserted=records_inserted)


if __name__ == "__main__":
    main()
