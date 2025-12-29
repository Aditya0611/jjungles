"""
Unit tests for engagement scraper adapter.

Tests the get_post_engagement function with various scenarios including
proxy failures, network errors, and successful data extraction.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import sys
from pathlib import Path

# Add parent directory to path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import get_post_engagement, detect_content_type, extract_post_caption
from tests.conftest import ProxyError, ProxyTimeoutError


class TestEngagementScraper:
    """Test suite for engagement scraper adapter."""
    
    def test_successful_engagement_extraction(self, mock_page_with_engagement):
        """Test successful extraction of engagement metrics."""
        post_url = "/p/ABC123/"
        mock_page_with_engagement.url = "https://www.instagram.com/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.detect_content_type', return_value='photo'):
            result = get_post_engagement(mock_page_with_engagement, post_url)
        
        assert result['likes'] > 0
        assert result['comments'] > 0
        assert 'total_engagement' in result
        assert 'format' in result
        assert result['total_engagement'] == result['likes'] + result['comments']
    
    def test_engagement_extraction_photo(self, mock_page):
        """Test engagement extraction for photo posts."""
        # Mock photo-specific selectors
        likes_element = MagicMock()
        likes_element.inner_text.return_value = "1,234 likes"
        
        comments_element = MagicMock()
        comments_element.inner_text.return_value = "56 comments"
        
        def locator_side_effect(selector):
            mock = MagicMock()
            if 'like' in selector.lower():
                mock.all.return_value = [likes_element]
                mock.first = likes_element
            elif 'comment' in selector.lower():
                mock.all.return_value = [comments_element]
                mock.first = comments_element
            else:
                mock.all.return_value = []
                mock.first = MagicMock()
                mock.first.inner_text.return_value = ""
            mock.count.return_value = 1
            return mock
        
        mock_page.locator.side_effect = locator_side_effect
        mock_page.url = "https://www.instagram.com/p/ABC123/"
        
        # Mock detect_content_type to return 'photo'
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.detect_content_type', return_value='photo'):
            result = get_post_engagement(mock_page, "/p/ABC123/")
        
        assert result['is_video'] is False
        assert result['format'] in ['photo', 'carousel']
        assert result['likes'] >= 0
        assert result['comments'] >= 0
    
    def test_engagement_extraction_reel(self, mock_page):
        """Test engagement extraction for reel posts."""
        # Mock reel-specific selectors with views
        views_element = MagicMock()
        views_element.inner_text.return_value = "50.2K views"
        
        likes_element = MagicMock()
        likes_element.inner_text.return_value = "5,234 likes"
        
        comments_element = MagicMock()
        comments_element.inner_text.return_value = "123 comments"
        
        def locator_side_effect(selector):
            mock = MagicMock()
            if 'view' in selector.lower():
                mock.all.return_value = [views_element]
                mock.first = views_element
            elif 'like' in selector.lower():
                mock.all.return_value = [likes_element]
                mock.first = likes_element
            elif 'comment' in selector.lower():
                mock.all.return_value = [comments_element]
                mock.first = comments_element
            else:
                mock.all.return_value = []
                mock.first = MagicMock()
                mock.first.inner_text.return_value = ""
            mock.count.return_value = 1
            return mock
        
        mock_page.locator.side_effect = locator_side_effect
        mock_page.url = "https://www.instagram.com/reel/XYZ789/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = get_post_engagement(mock_page, "/reel/XYZ789/")
        
        assert result['is_video'] is True
        assert result['format'] in ['reel', 'video']
        assert result['views'] > 0
    
    def test_proxy_failure_on_navigation(self, proxy_failure_page):
        """Test handling of proxy connection failure."""
        post_url = "/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            # Should handle proxy error gracefully
            result = get_post_engagement(proxy_failure_page, post_url)
        
        # Should return fallback data or empty structure
        assert isinstance(result, dict)
        assert 'likes' in result or 'total_engagement' in result
    
    def test_proxy_timeout(self, proxy_timeout_page):
        """Test handling of proxy timeout."""
        post_url = "/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = get_post_engagement(proxy_timeout_page, post_url)
        
        # Should handle timeout gracefully
        assert isinstance(result, dict)
    
    def test_proxy_auth_failure(self, proxy_auth_failure_page):
        """Test handling of proxy authentication failure."""
        post_url = "/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = get_post_engagement(proxy_auth_failure_page, post_url)
        
        # Should handle auth failure gracefully
        assert isinstance(result, dict)
    
    def test_network_error(self, network_error_page):
        """Test handling of general network errors."""
        post_url = "/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = get_post_engagement(network_error_page, post_url)
        
        # Should handle network error gracefully
        assert isinstance(result, dict)
    
    def test_missing_engagement_data(self, mock_page):
        """Test handling when engagement data is not found."""
        # Mock page with no engagement selectors
        def empty_locator(selector):
            mock = MagicMock()
            mock.all.return_value = []
            mock.count.return_value = 0
            mock.first = MagicMock()
            mock.first.inner_text.return_value = ""
            return mock
        
        mock_page.locator.side_effect = empty_locator
        mock_page.url = "https://www.instagram.com/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'), \
             patch('main.random.randint', return_value=1000):
            result = get_post_engagement(mock_page, "/p/ABC123/")
        
        # Should use fallback values
        assert result['likes'] >= 0
        assert result['comments'] >= 0
        assert result['total_engagement'] >= 0
    
    def test_content_type_detection_reel(self, mock_page):
        """Test content type detection for reels."""
        mock_page.url = "https://www.instagram.com/reel/ABC123/"
        
        result = detect_content_type(mock_page)
        assert result == 'reel'
    
    def test_content_type_detection_photo(self, mock_page):
        """Test content type detection for photos."""
        mock_page.url = "https://www.instagram.com/p/ABC123/"
        
        # Mock no carousel indicators
        mock_page.locator.return_value.count.return_value = 0
        
        result = detect_content_type(mock_page)
        assert result in ['photo', 'carousel']
    
    def test_caption_extraction(self, mock_page):
        """Test caption extraction from post."""
        caption_element = MagicMock()
        caption_element.inner_text.return_value = "This is a test caption #hashtag @mention"
        
        def locator_side_effect(selector):
            mock = MagicMock()
            if 'article' in selector or 'caption' in selector:
                mock.all.return_value = [caption_element]
                mock.first = caption_element
            else:
                mock.all.return_value = []
                mock.first = MagicMock()
                mock.first.inner_text.return_value = ""
            return mock
        
        mock_page.locator.side_effect = locator_side_effect
        
        with patch('main.logger'):
            caption = extract_post_caption(mock_page)
        
        assert len(caption) > 0
        assert 'hashtag' not in caption.lower()  # Should be cleaned
    
    def test_engagement_with_k_suffix(self, mock_page):
        """Test parsing engagement numbers with K suffix (e.g., 5.2K)."""
        likes_element = MagicMock()
        likes_element.inner_text.return_value = "5.2K likes"
        
        def locator_side_effect(selector):
            mock = MagicMock()
            if 'like' in selector.lower():
                mock.all.return_value = [likes_element]
                mock.first = likes_element
            else:
                mock.all.return_value = []
                mock.first = MagicMock()
                mock.first.inner_text.return_value = ""
            mock.count.return_value = 1
            return mock
        
        mock_page.locator.side_effect = locator_side_effect
        mock_page.url = "https://www.instagram.com/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = get_post_engagement(mock_page, "/p/ABC123/")
        
        # Should parse 5.2K as 5200
        assert result['likes'] == 5200
    
    def test_engagement_with_m_suffix(self, mock_page):
        """Test parsing engagement numbers with M suffix (e.g., 1.2M)."""
        likes_element = MagicMock()
        likes_element.inner_text.return_value = "1.2M likes"
        
        def locator_side_effect(selector):
            mock = MagicMock()
            if 'like' in selector.lower():
                mock.all.return_value = [likes_element]
                mock.first = likes_element
            else:
                mock.all.return_value = []
                mock.first = MagicMock()
                mock.first.inner_text.return_value = ""
            mock.count.return_value = 1
            return mock
        
        mock_page.locator.side_effect = locator_side_effect
        mock_page.url = "https://www.instagram.com/p/ABC123/"
        
        with patch('main.time.sleep'), patch('main.logger'):
            result = get_post_engagement(mock_page, "/p/ABC123/")
        
        # Should parse 1.2M as 1200000
        assert result['likes'] == 1200000

