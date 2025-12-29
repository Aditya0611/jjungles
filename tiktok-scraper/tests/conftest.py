"""
Pytest fixtures for scraper adapter tests.
Provides common fixtures for mocking Playwright, browser contexts, and proxy configurations.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional
from datetime import datetime, timezone


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_page():
    """Create a mock Playwright page object."""
    page = AsyncMock()
    page.url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
    page.title = AsyncMock(return_value="TikTok Creative Center")
    page.content = AsyncMock(return_value="<html><body><div>Hashtag content</div></body></html>")
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.evaluate = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.move = AsyncMock()
    page.reload = AsyncMock()
    page.add_init_script = AsyncMock()
    return page


@pytest.fixture
def mock_context(mock_page):
    """Create a mock Playwright browser context."""
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    context.close = AsyncMock()
    return context


@pytest.fixture
def mock_browser(mock_context):
    """Create a mock Playwright browser."""
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=mock_context)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_playwright(mock_browser):
    """Create a mock Playwright instance."""
    playwright = MagicMock()
    playwright.chromium = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    
    # Create async context manager
    async def async_enter():
        return playwright
    
    async def async_exit(*args):
        pass
    
    playwright.__aenter__ = AsyncMock(return_value=playwright)
    playwright.__aexit__ = AsyncMock(return_value=None)
    
    return playwright


@pytest.fixture
def mock_hashtag_html():
    """Sample HTML content with hashtag elements."""
    return """
    <html>
        <body>
            <div data-testid="hashtag_item">
                <span>1#Viral</span>
                <span>1.5M Posts</span>
            </div>
            <div data-testid="hashtag_item">
                <span>2#Trending</span>
                <span>500K Posts</span>
            </div>
            <div data-testid="hashtag_item">
                <span>3#Challenge</span>
                <span>2.3M Posts</span>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_scraped_data():
    """Sample scraped hashtag data."""
    return [
        {
            "rank": 1,
            "hashtag": "#Viral",
            "posts": "1.5M",
            "views": "N/A",
            "category": "General",
            "caption": None,
            "title": "#Viral",
            "post_format": "video",
            "sound_name": None,
            "sound_artist": None,
            "sound_id": None,
            "original_sound": False,
            "language": "en",
            "language_confidence": 0.95,
            "engagement_score": 8.5,
            "sentiment_polarity": 0.2,
            "sentiment_label": "Positive"
        },
        {
            "rank": 2,
            "hashtag": "#Trending",
            "posts": "500K",
            "views": "N/A",
            "category": "General",
            "caption": None,
            "title": "#Trending",
            "post_format": "video",
            "sound_name": None,
            "sound_artist": None,
            "sound_id": None,
            "original_sound": False,
            "language": "en",
            "language_confidence": 0.92,
            "engagement_score": 7.2,
            "sentiment_polarity": 0.0,
            "sentiment_label": "Neutral"
        }
    ]


@pytest.fixture
def proxy_config():
    """Proxy configuration for testing."""
    return {
        "server": "http://proxy.example.com:8080",
        "username": "test_user",
        "password": "test_pass"
    }


@pytest.fixture
def proxy_config_no_auth():
    """Proxy configuration without authentication."""
    return {
        "server": "http://proxy.example.com:8080"
    }


@pytest.fixture
def env_vars_with_proxy(monkeypatch, proxy_config):
    """Set environment variables with proxy configuration."""
    monkeypatch.setenv("PROXY_SERVER", proxy_config["server"])
    monkeypatch.setenv("PROXY_USERNAME", proxy_config["username"])
    monkeypatch.setenv("PROXY_PASSWORD", proxy_config["password"])
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test_key")
    return proxy_config


@pytest.fixture
def env_vars_no_proxy(monkeypatch):
    """Set environment variables without proxy."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test_key")
    monkeypatch.delenv("PROXY_SERVER", raising=False)
    monkeypatch.delenv("PROXY_USERNAME", raising=False)
    monkeypatch.delenv("PROXY_PASSWORD", raising=False)


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    client.table = MagicMock(return_value=client)
    client.insert = MagicMock(return_value=client)
    client.select = MagicMock(return_value=client)
    client.eq = MagicMock(return_value=client)
    client.gte = MagicMock(return_value=client)
    client.order = MagicMock(return_value=client)
    client.execute = MagicMock(return_value=MagicMock(data=[]))
    return client


@pytest.fixture
def mock_view_more_button():
    """Create a mock View More button element."""
    button = AsyncMock()
    button.is_visible = AsyncMock(return_value=True)
    button.scroll_into_view_if_needed = AsyncMock()
    button.click = AsyncMock()
    button.evaluate = AsyncMock()
    return button

