"""
Proxy-aware wrapper functions for browser operations.
These wrappers enable automatic proxy rotation on failure using ProxyPool.execute_with_retry().
"""
import logging
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


def create_browser_context_with_retry(browser, proxy_pool, max_retries=3):
    """
    Create browser context with automatic proxy rotation on failure.
    
    Args:
        browser: Playwright browser instance
        proxy_pool: ProxyPool instance (or None for no proxy)
        max_retries: Maximum retry attempts
        
    Returns:
        tuple: (context, proxy_used) or (None, None) on failure
    """
    # Import Config from models
    from models import Config
    
    # Enforce proxy if required
    if Config.REQUIRE_PROXIES and not proxy_pool:
        error_msg = "Browser context creation failed: Proxies are strictly required (REQUIRE_PROXIES=true) but no proxy pool provided."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def _create_context_with_proxy(proxy=None):
        """Inner function that creates context with given proxy."""
        context_options = {
            'viewport': {'width': Config.VIEWPORT_WIDTH, 'height': Config.VIEWPORT_HEIGHT},
            'locale': Config.LOCALE,
            'timezone_id': Config.TIMEZONE,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'extra_http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        }
        
        # Add proxy configuration if provided
        if proxy:
            proxy_config = {'server': proxy['server']}
            if 'username' in proxy and 'password' in proxy:
                proxy_config['username'] = proxy['username']
                proxy_config['password'] = proxy['password']
            if Config.PROXY_BYPASS:
                proxy_config['bypass'] = Config.PROXY_BYPASS
            context_options['proxy'] = proxy_config
            
            logger.info(f"Creating context with proxy: {proxy['server']}")
            print(f"    🔒 Using proxy: {proxy['server'].split('@')[-1] if '@' in proxy['server'] else proxy['server']}")
        
        # Create context
        context = browser.new_context(**context_options)
        
        # Hide automation indicators
        context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Enhanced Permissions Mock
            if (!window.Notification) {
                window.Notification = { permission: 'default' };
            }
            
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Mock Plugins and Hardware
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

            // Fix for "automation detection" via broken iframe props
            const originalGet = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow').get;
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
              get: function() {
                return originalGet.apply(this);
              }
            });
        """)
        
        return context
    
    # If proxy pool exists, use execute_with_retry
    if proxy_pool:
        try:
            context = proxy_pool.execute_with_retry(
                _create_context_with_proxy,
                operation_name="browser_context_creation"
            )
            # Get the last proxy used (from pool state)
            last_proxy = proxy_pool.get_next_proxy()
            return context, last_proxy
        except Exception as e:
            error_msg = f"Failed to create context with proxy pool after retries: {e}"
            logger.error(error_msg)
            # If proxies are required, we must fail hard
            if Config.REQUIRE_PROXIES:
                raise RuntimeError(error_msg)
            return None, None
    else:
        # No proxy pool provided
        if Config.REQUIRE_PROXIES:
            error_msg = "Browser context creation failed: Proxies are strictly required but no proxy pool available."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # No proxy pool, create context without proxy
        try:
            context = _create_context_with_proxy(proxy=None)
            return context, None
        except Exception as e:
            logger.error(f"Failed to create context without proxy: {e}")
            return None, None


def login_with_retry(browser, proxy_pool=None, max_retries=3):
    """
    Login to Instagram with automatic proxy rotation on failure.
    Creates a new context and page for each attempt to ensure fresh proxy usage.
    
    Args:
        browser: Playwright browser instance
        proxy_pool: ProxyPool instance (or None for no retry)
        max_retries: Maximum retry attempts
        
    Returns:
        tuple: (context, page, success) - context and page are open if success is True
    """
    # Import from models
    from auth import login_instagram
    from models import Config
    
    logger.info(f"Starting login with retry (max_retries={max_retries})")
    
    # If no proxy pool, just do a single attempt with default context (if allowed)
    if not proxy_pool:
        if Config.REQUIRE_PROXIES:
            error_msg = "Login failed: Proxies are strictly required but no proxy pool provided."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        try:
            context, _ = create_browser_context_with_retry(browser, None)
            if not context:
                return None, None, False
                
            page = context.new_page()
            if login_instagram(page):
                return context, page, True
            else:
                context.close()
                return None, None, False
        except Exception as e:
            logger.error(f"Login failed without proxy: {e}")
            return None, None, False

    # Retry loop with proxy rotation
    for attempt in range(max_retries):
        logger.info(f"Login attempt {attempt + 1}/{max_retries}")
        if attempt > 0:
            print(f"    🔄 Retrying with next proxy (Attempt {attempt + 1}/{max_retries})...")
        
        context = None
        page = None
        
        try:
            # 1. Create new context with a fresh proxy
            # We use max_retries=1 here because we want to handle the retry loop 
            # at this level (full login flow), not just at context creation level.
            context, proxy_used = create_browser_context_with_retry(browser, proxy_pool, max_retries=1)
            
            if not context:
                logger.warning(f"Failed to create browser context on attempt {attempt + 1}")
                continue
                
            # 2. Create new page
            page = context.new_page()
            
            # 3. Try login
            if login_instagram(page):
                logger.info(f"Login successful on attempt {attempt + 1}")
                return context, page, True
            else:
                logger.warning(f"Login failed on attempt {attempt + 1}")
                # Close context to clear state/proxy connection before next attempt
                try:
                    page.close()
                    context.close()
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Login attempt {attempt + 1} failed with error: {e}")
            try:
                if page: page.close()
                if context: context.close()
            except:
                pass
                
    logger.error("All login attempts failed")
    return None, None, False


def discover_hashtags_with_retry(page, proxy_pool=None, max_retries=3):
    """
    Discover trending hashtags with automatic proxy rotation on failure.
    
    Args:
        page: Playwright page instance
        proxy_pool: ProxyPool instance (or None for no retry)
        max_retries: Maximum retry attempts
        
    Returns:
        list: Discovered hashtag data or empty list on failure
    """
    # Import from discovery
    from discovery import discover_hashtags
    
    def _discover_operation(proxy=None):
        """Inner function for hashtag discovery that can be retried."""
        # Note: We cannot easily switch proxy for an existing page/context mid-session.
        # If proxy is provided here, it's from the retry logic, but we can't apply it 
        # to the 'page' object which was passed in.
        # Ideally, we would need to restart the session (login) to switch proxies.
        if proxy:
            # This is a limitation: we can't switch proxy on the fly for the same page
            pass
            
        hashtags = discover_hashtags(page)
        if not hashtags:
            raise Exception("No hashtags discovered")
        return hashtags
    
    # If proxy pool exists, use execute_with_retry
    if proxy_pool:
        try:
            result = proxy_pool.execute_with_retry(
                _discover_operation,
                operation_name="discover_trending_hashtags"
            )
            return result
        except Exception as e:
            error_msg = f"Hashtag discovery failed after all proxy retries: {e}"
            logger.error(error_msg)
            # Always raise on blockage/retry exhaustion
            raise RuntimeError(error_msg)
    else:
        # No proxy pool, try once
        try:
            hashtags = discover_hashtags(page)
            if not hashtags:
                error_msg = "Hashtag discovery failed (no results discovered)"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            return hashtags
        except Exception as e:
            logger.error(f"Hashtag discovery failed: {e}")
            raise
