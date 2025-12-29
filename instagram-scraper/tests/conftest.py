"""
Pytest fixtures for Instagram scraper tests.

Provides shared fixtures for mocking Playwright pages, proxy configurations,
sample data, and error scenarios.
"""
import pytest
from unittest.mock import MagicMock, Mock
from typing import Dict, Any, List
import os


@pytest.fixture
def mock_page():
    """Create a mock Playwright page object."""
    page = MagicMock()
    page.url = "https://www.instagram.com/explore/"
    page.content.return_value = "<html><body>Instagram Content</body></html>"
    page.title.return_value = "Instagram"
    
    # Mock locator chain
    mock_locator = MagicMock()
    mock_element = MagicMock()
    mock_element.inner_text.return_value = "1,234 likes"
    mock_element.is_visible.return_value = True
    mock_element.count.return_value = 1
    mock_locator.first = mock_element
    mock_locator.all.return_value = [mock_element]
    mock_locator.count.return_value = 1
    page.locator.return_value = mock_locator
    
    # Mock navigation
    page.goto = MagicMock(return_value=None)
    page.wait_for_selector = MagicMock(return_value=None)
    page.wait_for_load_state = MagicMock(return_value=None)
    
    return page


@pytest.fixture
def mock_page_with_engagement(mock_page):
    """Mock page with engagement data selectors."""
    page = mock_page
    
    # Mock likes element
    likes_element = MagicMock()
    likes_element.inner_text.return_value = "5,234 likes"
    
    # Mock comments element
    comments_element = MagicMock()
    comments_element.inner_text.return_value = "123 comments"
    
    # Mock views element (for videos/reels)
    views_element = MagicMock()
    views_element.inner_text.return_value = "50.2K views"
    
    # Mock caption element
    caption_element = MagicMock()
    caption_element.inner_text.return_value = "This is a test caption with #hashtag"
    
    def locator_side_effect(selector):
        mock = MagicMock()
        if 'like' in selector.lower():
            mock.all.return_value = [likes_element]
            mock.first = likes_element
        elif 'comment' in selector.lower():
            mock.all.return_value = [comments_element]
            mock.first = comments_element
        elif 'view' in selector.lower():
            mock.all.return_value = [views_element]
            mock.first = views_element
        elif 'caption' in selector.lower() or 'article' in selector.lower():
            mock.all.return_value = [caption_element]
            mock.first = caption_element
        else:
            mock.all.return_value = []
            mock.first = MagicMock()
            mock.first.inner_text.return_value = ""
        mock.count.return_value = 1
        return mock
    
    page.locator.side_effect = locator_side_effect
    return page


@pytest.fixture
def mock_page_with_hashtags(mock_page):
    """Mock page with hashtag discovery data."""
    page = mock_page
    page.url = "https://www.instagram.com/explore/"
    
    # Mock hashtag links
    hashtag_link = MagicMock()
    hashtag_link.get_attribute.return_value = "/explore/tags/trending/"
    hashtag_link.inner_text.return_value = "#trending"
    
    hashtag_locator = MagicMock()
    hashtag_locator.all.return_value = [hashtag_link] * 10
    hashtag_locator.count.return_value = 10
    
    def locator_side_effect(selector):
        if 'a[href*="/explore/tags/"]' in selector or 'a[href*="/tags/"]' in selector:
            return hashtag_locator
        else:
            mock = MagicMock()
            mock.all.return_value = []
            mock.count.return_value = 0
            return mock
    
    page.locator.side_effect = locator_side_effect
    return page


@pytest.fixture
def proxy_config():
    """Standard proxy configuration."""
    return {
        'server': 'http://127.0.0.1:8080',
        'username': 'test_user',
        'password': 'test_pass'
    }


@pytest.fixture
def proxy_config_no_auth():
    """Proxy configuration without authentication."""
    return {
        'server': 'http://127.0.0.1:8080'
    }


@pytest.fixture
def proxy_config_socks5():
    """SOCKS5 proxy configuration."""
    return {
        'server': 'socks5://127.0.0.1:1080',
        'username': 'test_user',
        'password': 'test_pass'
    }


@pytest.fixture
def sample_engagement_data():
    """Sample engagement data from a post."""
    return {
        'likes': 5234,
        'comments': 123,
        'views': 50200,
        'total_engagement': 5357,
        'is_video': True,
        'format': 'reel',
        'caption': 'This is a test caption with #hashtag',
        'language': 'en',
        'language_confidence': 0.95,
        'language_detected': True,
        'sentiment': {
            'polarity': 0.15,
            'label': 'positive',
            'emoji': '😊',
            'combined_score': 0.2
        }
    }


@pytest.fixture
def sample_hashtag_data():
    """Sample hashtag discovery data."""
    return {
        'hashtag': 'trending',
        'frequency': 5,
        'posts_count': 10,
        'sample_posts': [
            '/p/ABC123/',
            '/p/DEF456/',
            '/p/GHI789/'
        ],
        'category': 'general'
    }


@pytest.fixture
def sample_trend_summary():
    """Sample trend aggregation summary."""
    return {
        'avg_likes': 5000.0,
        'avg_comments': 150.0,
        'avg_engagement': 5150.0,
        'avg_views': 50000.0,
        'total_engagement': 15450.0,
        'total_views': 150000.0,
        'video_count': 2,
        'sentiment_summary': {
            'positive': 2,
            'neutral': 1,
            'negative': 0,
            'avg_polarity': 0.15,
            'avg_combined_score': 0.2,
            'overall_label': 'positive',
            'overall_emoji': '😊',
            'total_analyzed': 3
        },
        'language_summary': {
            'primary_language': 'en',
            'primary_language_percent': 100.0,
            'primary_language_count': 3,
            'avg_confidence': 0.95,
            'detected_count': 3,
            'total_analyzed': 3,
            'distribution': {'en': 3},
            'detection_rate': 100.0
        },
        'content_types': {'reel': 2, 'photo': 1},
        'primary_format': 'reel'
    }


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    
    # Mock successful insert
    insert_result = MagicMock()
    insert_result.data = [{'id': 1, 'topic_hashtag': 'test'}]
    table_mock.insert.return_value.execute.return_value = insert_result
    
    # Mock select query
    select_result = MagicMock()
    select_result.data = []
    table_mock.select.return_value.eq.return_value.execute.return_value = select_result
    
    return client


class ProxyError(Exception):
    """Custom exception for proxy failures."""
    pass


class ProxyTimeoutError(Exception):
    """Custom exception for proxy timeouts."""
    pass


@pytest.fixture
def proxy_failure_page():
    """Mock page that simulates proxy connection failure."""
    page = MagicMock()
    
    def goto_side_effect(*args, **kwargs):
        raise ProxyError("Proxy connection failed: Connection refused")
    
    page.goto.side_effect = goto_side_effect
    page.url = "https://www.instagram.com/"
    return page


@pytest.fixture
def proxy_timeout_page():
    """Mock page that simulates proxy timeout."""
    page = MagicMock()
    
    def goto_side_effect(*args, **kwargs):
        raise ProxyTimeoutError("Proxy timeout: Connection timed out after 30 seconds")
    
    page.goto.side_effect = goto_side_effect
    page.url = "https://www.instagram.com/"
    return page


@pytest.fixture
def proxy_auth_failure_page():
    """Mock page that simulates proxy authentication failure."""
    page = MagicMock()
    
    def goto_side_effect(*args, **kwargs):
        raise ProxyError("Proxy authentication failed: Invalid credentials")
    
    page.goto.side_effect = goto_side_effect
    page.url = "https://www.instagram.com/"
    return page


@pytest.fixture
def network_error_page():
    """Mock page that simulates general network errors."""
    page = MagicMock()
    
    def goto_side_effect(*args, **kwargs):
        raise ConnectionError("Network error: Unable to reach server")
    
    page.goto.side_effect = goto_side_effect
    page.url = "https://www.instagram.com/"
    return page


@pytest.fixture
def mock_playwright_context():
    """Mock Playwright browser context with proxy support."""
    context = MagicMock()
    
    # Mock context options
    context_options = {
        'proxy': {
            'server': 'http://127.0.0.1:8080'
        }
    }
    
    return context, context_options


@pytest.fixture
def sample_post_urls():
    """Sample Instagram post URLs."""
    return [
        '/p/ABC123/',
        '/reel/XYZ789/',
        '/p/DEF456/',
        '/tv/VIDEO123/'
    ]


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration with environment variables."""
    monkeypatch.setenv('INSTAGRAM_USERNAME', 'test_user')
    monkeypatch.setenv('INSTAGRAM_PASSWORD', 'test_pass')
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'test_key')
    monkeypatch.setenv('PROXY_SERVER', 'http://127.0.0.1:8080')
    monkeypatch.setenv('PROXY_USERNAME', 'proxy_user')
    monkeypatch.setenv('PROXY_PASSWORD', 'proxy_pass')
    monkeypatch.setenv('ENABLE_LANGUAGE_DETECTION', 'true')
    monkeypatch.setenv('MIN_LANGUAGE_CONFIDENCE', '0.5')
    
    return {
        'USERNAME': 'test_user',
        'PASSWORD': 'test_pass',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key',
        'PROXY_SERVER': 'http://127.0.0.1:8080',
        'PROXY_USERNAME': 'proxy_user',
        'PROXY_PASSWORD': 'proxy_pass'
    }

