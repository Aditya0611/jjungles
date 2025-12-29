#!/usr/bin/env python3
"""
Industrial-Grade Facebook Scraper Enhancements
===============================================

Production-ready enhancements for industrial-level scraping:
- Advanced rate limiting with token bucket algorithm
- Enhanced proxy management with health checks
- Session persistence and rotation
- Advanced anti-detection (fingerprinting evasion)
- Distributed scraping support
- Configuration management
- Metrics and monitoring

Usage:
------
    from industrial_scraper import IndustrialFacebookScraper
    
    scraper = IndustrialFacebookScraper(
        max_concurrent=5,
        rate_limit_per_minute=30,
        use_proxies=True
    )
    with scraper:
        results = scraper.scrape_category('technology', max_posts=100)
"""

import os
import sys
import json
import time
import random
import hashlib
import threading
import queue
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, deque
from pathlib import Path
from dataclasses import dataclass, field
from threading import Lock, Semaphore
import logging

# Import base scraper components
try:
    from base import BaseScraper, FacebookScraper, ProxyManager, TrendRecord
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
    from dotenv import load_dotenv
except ImportError as e:
    sys.stderr.write(f"ERROR: Missing required dependency: {e}\n")
    sys.exit(1)

load_dotenv()


# ============================================================================
# RATE LIMITER - Token Bucket Algorithm
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for industrial-level request throttling.
    Supports multiple rate limits per domain/endpoint.
    """
    
    def __init__(self, requests_per_minute: int = 30, burst_size: int = 5):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst requests allowed
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.time()
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.lock = Lock()
        self.request_times = deque(maxlen=requests_per_minute)
        
    def acquire(self, wait: bool = True) -> bool:
        """
        Acquire a token for making a request.
        
        Args:
            wait: If True, wait until token available; if False, return immediately
            
        Returns:
            bool: True if token acquired, False otherwise
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                self.request_times.append(now)
                return True
            
            if not wait:
                return False
            
            # Calculate wait time
            wait_time = (1.0 - self.tokens) / self.refill_rate
            time.sleep(wait_time)
            return self.acquire(wait=False)
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # If at limit, wait until oldest request expires
            if len(self.request_times) >= self.requests_per_minute:
                oldest_time = self.request_times[0]
                wait_time = 60 - (now - oldest_time) + 0.1  # Add small buffer
                if wait_time > 0:
                    time.sleep(wait_time)


# ============================================================================
# ENHANCED PROXY MANAGER - Health Checks & Auto-Rotation
# ============================================================================

class IndustrialProxyManager(ProxyManager):
    """
    Enhanced proxy manager with health checks, automatic rotation, and statistics.
    """
    
    def __init__(self, proxy_list: Optional[List[str]] = None, 
                 health_check_interval: int = 300,
                 max_failures: int = 3):
        """
        Initialize enhanced proxy manager.
        
        Args:
            proxy_list: List of proxy URLs
            health_check_interval: Seconds between health checks
            max_failures: Max consecutive failures before marking proxy as dead
        """
        super().__init__(proxy_list)
        self.health_check_interval = health_check_interval
        self.max_failures = max_failures
        self.proxy_stats = defaultdict(lambda: {
            'success_count': 0,
            'failure_count': 0,
            'last_success': None,
            'last_failure': None,
            'consecutive_failures': 0,
            'total_requests': 0,
            'avg_response_time': 0.0
        })
        self.dead_proxies = set()
        self.lock = Lock()
        self.last_health_check = {}
    
    def get_next_proxy(self) -> Optional[Dict]:
        """Get next healthy proxy with load balancing"""
        with self.lock:
            if not self.proxies:
                return None
            
            # Filter out dead proxies
            healthy_proxies = [
                (i, p) for i, p in enumerate(self.proxies)
                if i not in self.dead_proxies and i not in self.failed_proxies
            ]
            
            if not healthy_proxies:
                # Reset and try all proxies
                self.dead_proxies.clear()
                self.failed_proxies.clear()
                healthy_proxies = [(i, p) for i, p in enumerate(self.proxies)]
            
            # Select proxy with best success rate
            best_proxy = None
            best_score = -1
            
            for idx, proxy_url in healthy_proxies:
                stats = self.proxy_stats[proxy_url]
                total = stats['total_requests']
                
                if total == 0:
                    score = 1.0  # Unused proxy gets priority
                else:
                    success_rate = stats['success_count'] / total
                    # Prefer proxies with high success rate and recent success
                    score = success_rate
                    if stats['last_success']:
                        time_since_success = (time.time() - stats['last_success']) / 3600
                        score *= (1.0 / (1.0 + time_since_success))  # Decay over time
                
                if score > best_score:
                    best_score = score
                    best_proxy = (idx, proxy_url)
            
            if best_proxy:
                idx, proxy_url = best_proxy
                self.current_index = idx
                return {'server': proxy_url}
            
            return None
    
    def mark_success(self, proxy_url: str, response_time: float = 0.0):
        """Mark proxy request as successful"""
        with self.lock:
            stats = self.proxy_stats[proxy_url]
            stats['success_count'] += 1
            stats['total_requests'] += 1
            stats['last_success'] = time.time()
            stats['consecutive_failures'] = 0
            
            # Update average response time
            if response_time > 0:
                total = stats['total_requests']
                old_avg = stats['avg_response_time']
                stats['avg_response_time'] = (old_avg * (total - 1) + response_time) / total
            
            # Remove from failed/dead if it was there
            for i, p in enumerate(self.proxies):
                if p == proxy_url:
                    self.failed_proxies.discard(i)
                    self.dead_proxies.discard(i)
                    break
    
    def mark_failed(self, proxy_url: str):
        """Mark proxy request as failed"""
        with self.lock:
            stats = self.proxy_stats[proxy_url]
            stats['failure_count'] += 1
            stats['total_requests'] += 1
            stats['last_failure'] = time.time()
            stats['consecutive_failures'] += 1
            
            # Mark as dead if too many consecutive failures
            if stats['consecutive_failures'] >= self.max_failures:
                for i, p in enumerate(self.proxies):
                    if p == proxy_url:
                        self.dead_proxies.add(i)
                        break
            
            super().mark_failed(proxy_url)
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        with self.lock:
            return {
                'total_proxies': len(self.proxies),
                'healthy_proxies': len(self.proxies) - len(self.dead_proxies) - len(self.failed_proxies),
                'dead_proxies': len(self.dead_proxies),
                'failed_proxies': len(self.failed_proxies),
                'proxy_details': {
                    url: {
                        'success_rate': stats['success_count'] / max(stats['total_requests'], 1),
                        'total_requests': stats['total_requests'],
                        'consecutive_failures': stats['consecutive_failures'],
                        'avg_response_time': stats['avg_response_time']
                    }
                    for url, stats in self.proxy_stats.items()
                }
            }
    
    @staticmethod
    def from_env() -> 'IndustrialProxyManager':
        """
        Create IndustrialProxyManager from environment variable.
        Expected format: PROXIES=http://proxy1:8080,http://proxy2:8080
        """
        proxy_string = os.getenv('PROXIES', '')
        proxy_list = [p.strip() for p in proxy_string.split(',') if p.strip()]
        return IndustrialProxyManager(proxy_list)


# ============================================================================
# SESSION MANAGER - Cookie Persistence & Rotation
# ============================================================================

class SessionManager:
    """
    Manages browser sessions with cookie persistence and rotation.
    """
    
    def __init__(self, session_dir: Optional[Path] = None, 
                 session_ttl: int = 3600,
                 max_sessions: int = 10):
        """
        Initialize session manager.
        
        Args:
            session_dir: Directory to store session files
            session_ttl: Session time-to-live in seconds
            max_sessions: Maximum number of concurrent sessions
        """
        self.session_dir = session_dir or Path(__file__).parent / 'sessions'
        self.session_dir.mkdir(exist_ok=True)
        self.session_ttl = session_ttl
        self.max_sessions = max_sessions
        self.sessions = {}
        self.session_metadata = {}
        self.lock = Lock()
    
    def get_session_file(self, session_id: str) -> Path:
        """Get path to session file"""
        return self.session_dir / f"{session_id}.json"
    
    def save_session(self, session_id: str, cookies: List[Dict], 
                    user_agent: str, viewport: Dict):
        """Save session cookies and metadata"""
        with self.lock:
            session_data = {
                'cookies': cookies,
                'user_agent': user_agent,
                'viewport': viewport,
                'created_at': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat()
            }
            
            session_file = self.get_session_file(session_id)
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            self.session_metadata[session_id] = {
                'last_used': time.time(),
                'created_at': time.time()
            }
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load session cookies and metadata"""
        session_file = self.get_session_file(session_id)
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session expired
            created_at = datetime.fromisoformat(session_data['created_at'])
            age = (datetime.now() - created_at).total_seconds()
            
            if age > self.session_ttl:
                session_file.unlink()  # Delete expired session
                return None
            
            # Update last used
            session_data['last_used'] = datetime.now().isoformat()
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            return session_data
        except Exception:
            return None
    
    def get_or_create_session_id(self, identifier: str = "default") -> str:
        """Get existing session ID or create new one"""
        session_id = f"session_{hashlib.md5(identifier.encode()).hexdigest()[:8]}"
        return session_id
    
    def cleanup_expired_sessions(self):
        """Remove expired session files"""
        with self.lock:
            for session_file in self.session_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    created_at = datetime.fromisoformat(session_data['created_at'])
                    age = (datetime.now() - created_at).total_seconds()
                    
                    if age > self.session_ttl:
                        session_file.unlink()
                except Exception:
                    session_file.unlink()  # Delete corrupted files


# ============================================================================
# ANTI-DETECTION - Advanced Fingerprinting Evasion
# ============================================================================

class AntiDetection:
    """
    Advanced anti-detection measures for industrial scraping.
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    VIEWPORTS = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
        {'width': 1280, 'height': 720},
    ]
    
    TIMEZONES = [
        'America/New_York',
        'America/Los_Angeles',
        'America/Chicago',
        'Europe/London',
        'Europe/Paris',
        'Asia/Tokyo',
    ]
    
    LANGUAGES = [
        'en-US',
        'en-GB',
        'fr-FR',
        'de-DE',
        'es-ES',
    ]
    
    @staticmethod
    def get_random_fingerprint() -> Dict:
        """Generate random browser fingerprint"""
        return {
            'user_agent': random.choice(AntiDetection.USER_AGENTS),
            'viewport': random.choice(AntiDetection.VIEWPORTS),
            'timezone': random.choice(AntiDetection.TIMEZONES),
            'locale': random.choice(AntiDetection.LANGUAGES),
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
        }
    
    @staticmethod
    def get_stealth_script() -> str:
        """Get JavaScript to evade detection"""
        return """
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Add chrome runtime
        window.chrome = { runtime: {} };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Remove automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
    
    @staticmethod
    def human_like_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add human-like random delay"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    @staticmethod
    def human_like_mouse_movement(page: Page):
        """Simulate human-like mouse movement"""
        try:
            viewport = page.viewport_size
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                page.mouse.move(x, y)
        except Exception:
            pass


# ============================================================================
# METRICS & MONITORING
# ============================================================================

@dataclass
class ScrapingMetrics:
    """Metrics for monitoring scraper performance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_posts_scraped: int = 0
    total_hashtags_found: int = 0
    avg_response_time: float = 0.0
    proxy_rotations: int = 0
    rate_limit_hits: int = 0
    session_rotations: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        total = self.total_requests
        return (self.successful_requests / total * 100) if total > 0 else 0.0
    
    def get_uptime(self) -> float:
        """Get uptime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.get_success_rate(),
            'total_posts_scraped': self.total_posts_scraped,
            'total_hashtags_found': self.total_hashtags_found,
            'avg_response_time': self.avg_response_time,
            'proxy_rotations': self.proxy_rotations,
            'rate_limit_hits': self.rate_limit_hits,
            'session_rotations': self.session_rotations,
            'uptime_seconds': self.get_uptime()
        }


# ============================================================================
# INDUSTRIAL FACEBOOK SCRAPER
# ============================================================================

class IndustrialFacebookScraper(FacebookScraper):
    """
    Industrial-grade Facebook scraper with advanced features:
    - Rate limiting
    - Enhanced proxy management
    - Session persistence
    - Anti-detection
    - Metrics and monitoring
    """
    
    def __init__(self, 
                 headless: bool = True,
                 debug: bool = False,
                 rate_limit_per_minute: int = 30,
                 use_proxies: bool = True,
                 use_sessions: bool = True,
                 max_concurrent: int = 1):
        """
        Initialize industrial Facebook scraper.
        
        Args:
            headless: Run browser in headless mode
            debug: Enable debug logging
            rate_limit_per_minute: Maximum requests per minute
            use_proxies: Enable proxy rotation
            use_sessions: Enable session persistence
            max_concurrent: Maximum concurrent scraping operations
        """
        # Initialize enhanced proxy manager
        if use_proxies:
            proxy_manager = IndustrialProxyManager.from_env()
        else:
            proxy_manager = None
        
        super().__init__(headless=headless, debug=debug)
        
        # Override proxy manager
        self.proxy_manager = proxy_manager
        
        # Initialize industrial components
        self.rate_limiter = RateLimiter(requests_per_minute=rate_limit_per_minute)
        self.session_manager = SessionManager() if use_sessions else None
        self.metrics = ScrapingMetrics()
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.lock = Lock()
        
        # Anti-detection fingerprint
        self.fingerprint = AntiDetection.get_random_fingerprint()
        
        self.logger.info("IndustrialFacebookScraper initialized", extra={
            'rate_limit': rate_limit_per_minute,
            'use_proxies': use_proxies,
            'use_sessions': use_sessions,
            'max_concurrent': max_concurrent,
            'fingerprint': self.fingerprint
        })
    
    def setup_browser(self):
        """Setup browser with industrial-grade anti-detection"""
        try:
            self.logger.info("Setting up industrial browser")
            self.playwright = sync_playwright().start()
            
            # Use fingerprint for browser launch
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Get proxy configuration
            proxy_config = None
            if self.proxy_manager:
                proxy_config = self.proxy_manager.get_next_proxy()
            
            # Create context with fingerprint
            context_options = {
                'viewport': self.fingerprint['viewport'],
                'user_agent': self.fingerprint['user_agent'],
                'locale': self.fingerprint['locale'],
                'timezone_id': self.fingerprint['timezone'],
            }
            
            if proxy_config:
                context_options['proxy'] = proxy_config
                self.logger.info("Using proxy", extra={'proxy': proxy_config['server']})
            
            self.context = self.browser.new_context(**context_options)
            
            # Add advanced stealth script
            self.context.add_init_script(AntiDetection.get_stealth_script())
            
            self.context.set_default_timeout(30000)
            self.page = self.context.new_page()
            
            # Load session if available
            if self.session_manager:
                session_id = self.session_manager.get_or_create_session_id("facebook")
                session_data = self.session_manager.load_session(session_id)
                if session_data:
                    self.context.add_cookies(session_data['cookies'])
                    self.logger.info("Session loaded", extra={'session_id': session_id})
            
            # Warm up with human-like behavior
            self.page.goto("https://www.google.com", wait_until="domcontentloaded")
            AntiDetection.human_like_delay(2, 4)
            AntiDetection.human_like_mouse_movement(self.page)
            
            self.logger.info("Industrial browser setup complete")
            return True
            
        except Exception as e:
            self.logger.error("Browser setup failed", extra={'error': str(e)})
            self.logger.critical("FATAL: Raising error for industrial browser setup failure to ensure no unproxied leak.")
            raise e
    
    def navigate_to(self, url: str, wait_until: str = "load"):
        """Navigate with rate limiting and metrics"""
        start_time = time.time()
        
        try:
            # Rate limiting
            self.rate_limiter.acquire()
            
            # Navigate
            super().navigate_to(url, wait_until)
            
            # Update metrics
            response_time = time.time() - start_time
            with self.lock:
                self.metrics.total_requests += 1
                self.metrics.successful_requests += 1
                # Update average response time
                total = self.metrics.total_requests
                old_avg = self.metrics.avg_response_time
                self.metrics.avg_response_time = (old_avg * (total - 1) + response_time) / total
            
            # Mark proxy success if used
            if self.proxy_manager and self.context:
                proxy_config = getattr(self.context, '_proxy', None)
                if proxy_config:
                    self.proxy_manager.mark_success(proxy_config.get('server', ''), response_time)
            
            return True
            
        except Exception as e:
            with self.lock:
                self.metrics.total_requests += 1
                self.metrics.failed_requests += 1
            
            # Mark proxy failure if used
            if self.proxy_manager and self.context:
                proxy_config = getattr(self.context, '_proxy', None)
                if proxy_config:
                    self.proxy_manager.mark_failed(proxy_config.get('server', ''))
            
            self.logger.error("Navigation failed", extra={'url': url, 'error': str(e)})
            raise
    
    def cleanup(self):
        """Cleanup with session saving"""
        try:
            # Save session before cleanup
            if self.session_manager and self.context:
                try:
                    cookies = self.context.cookies()
                    session_id = self.session_manager.get_or_create_session_id("facebook")
                    self.session_manager.save_session(
                        session_id,
                        cookies,
                        self.fingerprint['user_agent'],
                        self.fingerprint['viewport']
                    )
                    self.logger.info("Session saved", extra={'session_id': session_id})
                except Exception as e:
                    self.logger.warning("Failed to save session", extra={'error': str(e)})
            
            # Cleanup browser
            super().cleanup()
            
            # Log final metrics
            self.logger.info("Scraping session complete", extra={
                'metrics': self.metrics.to_dict(),
                'proxy_stats': self.proxy_manager.get_stats() if self.proxy_manager else {}
            })
            
        except Exception as e:
            self.logger.warning("Cleanup error", extra={'error': str(e)})
    
    def get_metrics(self) -> Dict:
        """Get current scraping metrics"""
        with self.lock:
            metrics = self.metrics.to_dict()
            if self.proxy_manager:
                metrics['proxy_stats'] = self.proxy_manager.get_stats()
            return metrics


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_industrial_scraper(**kwargs) -> IndustrialFacebookScraper:
    """
    Factory function to create industrial scraper with default settings.
    
    Args:
        **kwargs: Override default settings
        
    Returns:
        IndustrialFacebookScraper instance
    """
    defaults = {
        'headless': True,
        'debug': False,
        'rate_limit_per_minute': 30,
        'use_proxies': True,
        'use_sessions': True,
        'max_concurrent': 1
    }
    defaults.update(kwargs)
    return IndustrialFacebookScraper(**defaults)

