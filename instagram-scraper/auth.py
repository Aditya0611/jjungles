import time
import logging
from typing import Optional, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

# Local imports
from models import (
    Config, ErrorCode, INSTAGRAM_LOGIN_URL, INSTAGRAM_BASE_URL,
    HOME_SELECTOR, USERNAME_SELECTORS, PASSWORD_FIELD_SELECTOR,
    SUBMIT_BUTTON_SELECTOR, COOKIE_CONSENT_SELECTORS, POPUP_SELECTORS,
    TIMEOUT_LOGIN_FORM, TIMEOUT_LOGIN_SUCCESS, TIMEOUT_PAGE_NAVIGATION,
    TIMEOUT_SELECTOR_WAIT, TIMEOUT_COOKIE_CONSENT, DELAY_PAGE_LOAD,
    DELAY_LOGIN_WAIT, DELAY_POPUP_DISMISS, DELAY_CREDENTIALS_MIN,
    DELAY_CREDENTIALS_MAX, DELAY_TYPING_MIN, DELAY_TYPING_MAX
)
from observability import metrics

# Logger instance
logger = logging.getLogger(__name__)

def verify_logged_in(page: Page) -> bool:
    """Verify that user is actually logged in to Instagram."""
    try:
        current_url = page.url
        logger.debug(f"Verifying login status. Current URL: {current_url}")
        
        if "/accounts/login" in current_url or "/auth_platform/codeentry" in current_url or "/challenge" in current_url:
            return False
        
        logged_in_indicators = [
            HOME_SELECTOR,
            "svg[aria-label='Home']",
            "a[href='/']",
            "nav[role='navigation']",
            "header[role='banner']",
            "svg[aria-label='New post']",
            "svg[aria-label='Direct']"
        ]
        
        found_indicators = sum(1 for selector in logged_in_indicators if page.locator(selector).first.is_visible(timeout=1500))
        
        if found_indicators >= 2:
            return True
            
        login_indicators = [
            "a:has-text('Log In')",
            "button:has-text('Log In')",
            "a:has-text('Sign Up')",
            "a[href*='/accounts/login']"
        ]
        
        for indicator in login_indicators:
            if page.locator(indicator).first.is_visible(timeout=1000):
                return False
                
        return found_indicators >= 1
    except Exception as e:
        logger.debug(f"Error verifying login status: {e}")
        return False

def wait_for_manual_login(page: Page, timeout: int = 120) -> bool:
    """Wait for user to manually log in through the browser."""
    logger.warning("Automated login failed - manual login required")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if verify_logged_in(page):
                logger.info("Manual login detected and verified")
                return True
            time.sleep(5)
        except Exception as e:
            logger.debug(f"Error during manual login check: {e}")
            time.sleep(5)
            
    return False

def login_instagram(page: Page, proxy_pool=None) -> bool:
    """Login to Instagram with provided credentials."""
    try:
        logger.info("Navigating to Instagram login page")
        
        # Navigate to login page
        start_time = time.time()
        page.goto(INSTAGRAM_LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT_PAGE_NAVIGATION)
        
        # Handle cookie consent
        for selector in COOKIE_CONSENT_SELECTORS:
            try:
                if page.locator(selector).first.is_visible(timeout=TIMEOUT_COOKIE_CONSENT):
                    page.locator(selector).first.click()
                    time.sleep(DELAY_POPUP_DISMISS)
                    break
            except:
                continue
                
        # Fill credentials
        user_field = None
        for selector in USERNAME_SELECTORS:
            try:
                if page.locator(selector).first.is_visible(timeout=TIMEOUT_LOGIN_FORM):
                    user_field = page.locator(selector).first
                    break
            except:
                continue
                
        if not user_field:
            logger.error(f"[{ErrorCode.AUTH_FAILED}] Username field not found")
            return False
            
        user_field.fill(Config.USERNAME)
        time.sleep(1)
        page.locator(PASSWORD_FIELD_SELECTOR).fill(Config.PASSWORD)
        time.sleep(1)
        page.locator(SUBMIT_BUTTON_SELECTOR).click()
        
        # Wait for login success
        try:
            page.wait_for_selector(HOME_SELECTOR, timeout=TIMEOUT_LOGIN_SUCCESS)
            logger.info("Login successful")
            metrics.increment('login_success_total')
            return True
        except:
            if not Config.HEADLESS:
                return wait_for_manual_login(page)
            return False
            
    except Exception as e:
        logger.error(f"[{ErrorCode.AUTH_FAILED}] Login error: {e}")
        metrics.increment('login_failures_total')
        return False
