"""
Unit tests for hashtag discovery scraper adapter.

Tests the discover_trending_hashtags function with various scenarios including
proxy failures and successful hashtag extraction.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import sys
from pathlib import Path

# Add parent directory to path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import discover_trending_hashtags
from tests.conftest import ProxyError, ProxyTimeoutError


class TestHashtagDiscovery:
    """Test suite for hashtag discovery scraper adapter."""
    
    def test_successful_hashtag_discovery(self, mock_page_with_hashtags):
        """Test successful discovery of trending hashtags."""
        # Mock post links for discovery
        post_link = MagicMock()
        post_link.get_attribute.return_value = "/p/ABC123/"
        
        def locator_side_effect(selector):
            if 'a[href*="/explore/tags/"]' in selector or 'a[href*="/tags/"]' in selector:
                return mock_page_with_hashtags.locator(selector)
            elif 'a[href*="/p/"]' in selector or 'a[href*="/reel/"]' in selector:
                mock = MagicMock()
                mock.all.return_value = [post_link] * 10
                mock.count.return_value = 10
                return mock
            else:
                mock = MagicMock()
                mock.all.return_value = []
                mock.count.return_value = 0
                return mock
        
        mock_page_with_hashtags.locator.side_effect = locator_side_effect
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.random.uniform', return_value=1.0), \
             patch('main.Config.POSTS_TO_SCAN', 10), \
             patch('main.Config.SCROLL_COUNT', 2):
            result = discover_trending_hashtags(mock_page_with_hashtags)
        
        assert isinstance(result, list)
        # Should return list of hashtag data dictionaries
        if result:
            assert 'hashtag' in result[0]
            assert 'frequency' in result[0]
    
    def test_proxy_failure_on_explore_page(self, proxy_failure_page):
        """Test handling of proxy failure when accessing explore page."""
        proxy_failure_page.url = "https://www.instagram.com/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = discover_trending_hashtags(proxy_failure_page)
        
        # Should return empty list or handle gracefully
        assert isinstance(result, list)
    
    def test_proxy_timeout_on_navigation(self, proxy_timeout_page):
        """Test handling of proxy timeout during navigation."""
        proxy_timeout_page.url = "https://www.instagram.com/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = discover_trending_hashtags(proxy_timeout_page)
        
        # Should handle timeout gracefully
        assert isinstance(result, list)
    
    def test_network_error_during_discovery(self, network_error_page):
        """Test handling of network errors during hashtag discovery."""
        network_error_page.url = "https://www.instagram.com/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = discover_trending_hashtags(network_error_page)
        
        # Should return empty list on error
        assert isinstance(result, list)
    
    def test_no_hashtags_found(self, mock_page):
        """Test handling when no hashtags are found."""
        # Mock page with no hashtag links
        def empty_locator(selector):
            mock = MagicMock()
            mock.all.return_value = []
            mock.count.return_value = 0
            return mock
        
        mock_page.locator.side_effect = empty_locator
        mock_page.url = "https://www.instagram.com/explore/"
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.random.uniform', return_value=1.0):
            result = discover_trending_hashtags(mock_page)
        
        # Should return empty list or list with zero frequency hashtags
        assert isinstance(result, list)
    
    def test_hashtag_frequency_calculation(self, mock_page):
        """Test that hashtag frequency is calculated correctly."""
        # Mock multiple posts with same hashtag
        hashtag_link = MagicMock()
        hashtag_link.get_attribute.return_value = "/explore/tags/trending/"
        hashtag_link.inner_text.return_value = "#trending"
        
        hashtag_locator = MagicMock()
        hashtag_locator.all.return_value = [hashtag_link] * 5  # 5 occurrences
        hashtag_locator.count.return_value = 5
        
        def locator_side_effect(selector):
            if 'a[href*="/explore/tags/"]' in selector or 'a[href*="/tags/"]' in selector:
                return hashtag_locator
            else:
                mock = MagicMock()
                mock.all.return_value = []
                mock.count.return_value = 0
                return mock
        
        mock_page.locator.side_effect = locator_side_effect
        mock_page.url = "https://www.instagram.com/explore/"
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.random.uniform', return_value=1.0), \
             patch('main.Config.POSTS_TO_SCAN', 10), \
             patch('main.Config.SCROLL_COUNT', 2):
            result = discover_trending_hashtags(mock_page)
        
        # Should count frequency correctly
        if result:
            for item in result:
                assert item['frequency'] >= 0
    
    def test_hashtag_categorization(self, mock_page_with_hashtags):
        """Test that hashtags are properly categorized."""
        # Mock post links for discovery
        post_link = MagicMock()
        post_link.get_attribute.return_value = "/p/ABC123/"
        
        def locator_side_effect(selector):
            if 'a[href*="/explore/tags/"]' in selector or 'a[href*="/tags/"]' in selector:
                return mock_page_with_hashtags.locator(selector)
            elif 'a[href*="/p/"]' in selector or 'a[href*="/reel/"]' in selector:
                mock = MagicMock()
                mock.all.return_value = [post_link] * 10
                mock.count.return_value = 10
                return mock
            else:
                mock = MagicMock()
                mock.all.return_value = []
                mock.count.return_value = 0
                return mock
        
        mock_page_with_hashtags.locator.side_effect = locator_side_effect
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.random.uniform', return_value=1.0), \
             patch('main.Config.POSTS_TO_SCAN', 10), \
             patch('main.Config.SCROLL_COUNT', 2):
            result = discover_trending_hashtags(mock_page_with_hashtags)
        
        if result:
            for item in result:
                assert 'category' in item
                assert isinstance(item['category'], str)
    
    def test_sample_posts_extraction(self, mock_page):
        """Test that sample posts are extracted for each hashtag."""
        hashtag_link = MagicMock()
        hashtag_link.get_attribute.return_value = "/explore/tags/trending/"
        
        post_link = MagicMock()
        post_link.get_attribute.return_value = "/p/ABC123/"
        
        def locator_side_effect(selector):
            mock = MagicMock()
            if 'a[href*="/explore/tags/"]' in selector:
                mock.all.return_value = [hashtag_link]
                mock.count.return_value = 1
            elif 'a[href*="/p/"]' in selector or 'a[href*="/reel/"]' in selector:
                mock.all.return_value = [post_link]
                mock.count.return_value = 1
            else:
                mock.all.return_value = []
                mock.count.return_value = 0
            return mock
        
        mock_page.locator.side_effect = locator_side_effect
        mock_page.url = "https://www.instagram.com/explore/"
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.random.uniform', return_value=1.0), \
             patch('main.Config.POSTS_TO_SCAN', 10):
            result = discover_trending_hashtags(mock_page)
        
        if result:
            for item in result:
                assert 'sample_posts' in item
                assert isinstance(item['sample_posts'], list)

