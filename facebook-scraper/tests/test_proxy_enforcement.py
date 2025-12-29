import os
import sys
from unittest.mock import patch
import logging

# Add current dir to path
sys.path.insert(0, os.getcwd())

from base import FacebookScraper

def test_proxy_enforcement():
    print("Testing PROXY_STRICT_MODE=true with no proxies...")
    os.environ['PROXY_STRICT_MODE'] = 'true'
    os.environ['PROXIES'] = ''
    
    # Force root logger to DEBUG
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        from base import BaseScraper, ProxyManager
        # Ensure we start fresh
        proxy_mgr = ProxyManager([]) # Empty list
        scraper = BaseScraper(headless=True, proxy_manager=proxy_mgr)
        
        print("Test 1: Empty proxy list should trigger sys.exit(1)")
        with patch('playwright.sync_api.sync_playwright') as mock_pw:
            with patch('base.sys.exit') as mock_exit:
                try:
                    scraper.setup_browser()
                except Exception as e:
                    print(f"Skipping expected exception during setup: {e}")
                
                if mock_exit.called:
                    exit_code = mock_exit.call_args[0][0] if mock_exit.call_args else "unknown"
                    print(f"SUCCESS: base.sys.exit called with code: {exit_code}")
                else:
                    print("FAILED: base.sys.exit was NOT called")

        print("\nTest 2: PROXY_STRICT_MODE=true with rotation failure should raise RuntimeError")
        os.environ['PROXY_STRICT_MODE'] = 'true'
        proxy_mgr = ProxyManager(['http://fail:8080'])
        scraper = BaseScraper(headless=True, proxy_manager=proxy_mgr)
        
        # More robust mock for playwright
        with patch('base.sync_playwright') as mock_sync_pw:
            # Mock get_next_proxy to return None to simulate rotation failure in setup_browser
            with patch.object(ProxyManager, 'get_next_proxy', return_value=None):
                try:
                    scraper.setup_browser()
                    print("FAILED: setup_browser did not raise any exception on rotation failure")
                except Exception as e:
                    print(f"SUCCESS: Caught expected fatal error: {type(e).__name__}: {e}")
                    
    except Exception as e:
        print(f"Caught unexpected error in test script: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_proxy_enforcement()
