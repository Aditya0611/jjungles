
import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Add parent directory to path to import the scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linkedin_hashtag_scraper_playwright import LinkedInHashtagScraper

class TestLinkedInScraperSmoke(unittest.TestCase):
    
    @patch('linkedin_hashtag_scraper_playwright.sync_playwright')
    @patch('linkedin_hashtag_scraper_playwright.create_client')
    @patch('linkedin_hashtag_scraper_playwright.logger')
    def setUp(self, mock_logger, mock_create_client, mock_playwright):
        self.mock_logger = mock_logger
        self.mock_create_client = mock_create_client
        self.mock_playwright = mock_playwright
        
        # Mock Supabase client
        self.mock_supabase = MagicMock()
        self.mock_create_client.return_value = self.mock_supabase
        
        # Mock Playwright
        self.mock_browser = MagicMock()
        self.mock_context = MagicMock()
        self.mock_page = MagicMock()
        
        self.mock_playwright_instance = MagicMock()
        self.mock_playwright.return_value.start.return_value = self.mock_playwright_instance
        self.mock_playwright_instance.chromium.launch.return_value = self.mock_browser
        self.mock_browser.new_context.return_value = self.mock_context
        self.mock_context.new_page.return_value = self.mock_page
        
        # Initialize scraper (headless=True to avoid GUI)
        self.scraper = LinkedInHashtagScraper(headless=True, use_supabase=True)
        # Mock the browser/page objects that are usually set in start() or setup_browser()
        self.scraper.playwright = self.mock_playwright_instance
        self.scraper.browser = self.mock_browser
        self.scraper.context = self.mock_context
        self.scraper.page = self.mock_page

    def test_initialization(self):
        """Test that scraper initializes correctly"""
        self.assertTrue(self.scraper.use_supabase)
        self.assertTrue(self.scraper.headless)
        self.assertIsNotNone(self.scraper.supabase)

    def test_save_to_supabase_mock(self):
        """Test save_to_supabase with mocked Supabase"""
        # Setup dummy data
        top_hashtags = [("test", 10)]
        self.scraper.hashtags = ["test"] * 10
        self.scraper.hashtag_contexts = {"test": ["context"]}
        self.scraper.hashtag_captions = {"test": ["caption"]}
        self.scraper.hashtag_languages = {"test": ["en"]}
        self.scraper.hashtag_sentiments = {"test": [{"consensus_label": "positive"}]}
        
        # Mock Supabase response
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        self.mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
        
        # Run method
        self.scraper.save_to_supabase(top_hashtags)
        
        # Verify call
        self.mock_supabase.table.assert_called_with("trends")
        self.mock_supabase.table().insert.assert_called()
        self.assertTrue(self.mock_supabase.table().insert().execute.called)

    def test_proxy_rotation_logic(self):
        """Test proxy rotation logic"""
        # Enable proxies
        self.scraper.use_proxies = True
        self.scraper.proxy_rotator = MagicMock()
        self.scraper.rotate_proxy_every = 5
        self.scraper.scroll_count = 5
        
        # Mock get_proxy_config
        new_proxy = {"server": "http://1.2.3.4:8080"}
        self.scraper.proxy_rotator.get_proxy_config.return_value = new_proxy
        
        # Run rotation
        self.scraper.rotate_proxy_if_needed()
        
        # Verify rotation happened
        self.scraper.proxy_rotator.get_proxy_config.assert_called()
        # Should have called proper setup/logging
        # We can't easily verify setup_browser call without more mocking because it's a method on self
        # But we can check if logger was called
        # The logger info "Rotating proxy..." should be called
        # Note: In our refactor we kept using global logger from module, which we patched in setUp class patcher
        # Actually I patched 'linkedin_hashtag_scraper_playwright.logger'
        
        # Since rotate_proxy_if_needed calls logger.info
        self.assertTrue(self.mock_logger.info.called)

    def test_run_with_retry_logic(self):
        """Test that retry logic exists (even if simple)"""
        # Only verify the method exists as we didn't fully implement a complex retry decorator, 
        # but we added retry logic inside methods.
        # We can test handle_linkedin_error retry logic if we mock check_for_linkedin_error
        
        self.scraper.check_for_linkedin_error = MagicMock(side_effect=[True, False]) # Error then Fixed
        self.scraper.page.query_selector.return_value = None # No "Try again" button
        self.scraper.page.reload = MagicMock()
        
        result = self.scraper.handle_linkedin_error(max_retries=2)
        
        self.assertTrue(result)
        self.assertTrue(self.scraper.page.reload.called)

    def test_start_with_failed_proxy(self):
        """Test start method handles proxy failure correctly"""
        self.scraper.use_proxies = True
        self.scraper.proxy_rotator = MagicMock()
        failed_proxy = {"server": "http://bad.proxy:8080"}
        self.scraper.proxy_rotator.get_proxy_config.return_value = failed_proxy
        
        # Mock setup_browser to raise exception when proxy is used
        # keeping original setup is not needed as we replace it on the instance
        
        def mock_setup(proxy=None):
            if proxy:
                raise Exception("Proxy Fail")
            # If None, do nothing (success)
            pass
            
        self.scraper.setup_browser = MagicMock(side_effect=mock_setup)

        # The new implementation should raise RuntimeError if all proxies fail
        with self.assertRaises(RuntimeError):
            self.scraper.start()
        
        # Verify mark_proxy_failed was called
        # Note: In our implementation, mark_proxy_failed is called inside the loop
        self.assertTrue(self.scraper.proxy_rotator.mark_proxy_failed.called)

if __name__ == '__main__':
    unittest.main()
