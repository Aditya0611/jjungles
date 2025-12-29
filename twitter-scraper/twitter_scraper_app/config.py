import os
import uuid
import random
from dotenv import load_dotenv
from typing import Optional, Dict
from twitter_scraper_app.utils import logger

# Load environment variables
load_dotenv()
logger.info("Attempting to load environment variables from .env file...")

# Version ID for this run
SCRAPE_VERSION_ID = str(uuid.uuid4())

# Nitter Config (Rotating mirrors for search/RSS)
# Note: Many instances have disabled RSS search. We try several to find a working one.
# If you see "getaddrinfo failed", your network or ISP might be blocking these domains.
NITTER_INSTANCES = [
    "https://nitter.privacy.com.de",
    "https://nitter.privacy.no",
    "https://nitter.no-logs.com",
    "https://nitter.tiekoetter.com",
    "https://nitter.privacyredirect.com",
    "https://nitter.poast.org"
]

class ProxyManager:
    """Manages proxy rotation and selection."""
    def __init__(self):
        self.proxies = []
        self.require_proxy = True # Hardcoded to True to prevent bypass
        self._load_proxies()

    def _load_proxies(self):
        # 1. Try PROXY_LIST env var (comma separated)
        proxy_list_str = os.getenv("PROXY_LIST")
        if proxy_list_str:
            self.proxies = [p.strip() for p in proxy_list_str.split(',') if p.strip()]
        
        # 2. Fallback to HTTP_PROXY/HTTPS_PROXY
        if not self.proxies:
            http_proxy = os.getenv("HTTP_PROXY")
            https_proxy = os.getenv("HTTPS_PROXY")
            if http_proxy: self.proxies.append(http_proxy)
            if https_proxy and https_proxy not in self.proxies: self.proxies.append(https_proxy)

        if self.proxies:
            masked_proxies = [p[:8] + "..." + p[-4:] if len(p) > 15 else "PROXY" for p in self.proxies]
            logger.info(f"Loaded {len(self.proxies)} proxies: {masked_proxies}")
        else:
            if self.require_proxy:
                logger.error("FATAL: REQUIRE_PROXY is set to true but no proxies were loaded.")
                raise RuntimeError("No proxies loaded while REQUIRE_PROXY is active.")
            logger.info("No proxies configured. Running directly.")

    def get_proxy(self) -> Dict[str, str]:
        if not self.proxies:
            logger.error("FATAL: get_proxy() called but no proxies are available.")
            raise RuntimeError("No proxies loaded while REQUIRE_PROXY is active.")
        
        proxy_url = random.choice(self.proxies)
        return {
            "http://": proxy_url,
            "https://": proxy_url,
            "all://": proxy_url 
        }

# Global instance
proxy_manager = ProxyManager()

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Test Mode Configuration
TEST_MODE = False
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials not found in .env file. Running in TEST MODE.")
    TEST_MODE = True
else:
    logger.info("Environment variables loaded successfully.")
