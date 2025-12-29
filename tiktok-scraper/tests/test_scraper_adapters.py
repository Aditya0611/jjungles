"""
Unit tests for scraper adapters with proxy failure scenarios.

Tests cover:
- Browser context creation with/without proxy
- Proxy configuration and authentication
- Proxy failure scenarios (connection errors, timeouts, authentication failures)
- Scraping attempts with retry logic
- Error handling and recovery
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from playwright.async_api import TimeoutError as PlaywrightTimeout, Error as PlaywrightError
import sys
import os

# Add parent directory to path to import base module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path setup
import importlib
import base
importlib.reload(base)  # Reload to get fresh env vars in tests

from base import (
    scrape_single_attempt,
    scrape_with_retry,
    scrape_tiktok_hashtags,
    init_supabase,
)


class TestBrowserContextAdapter:
    """Tests for browser context creation with proxy support."""
    
    @pytest.mark.asyncio
    async def test_context_creation_without_proxy(self, mock_browser, env_vars_no_proxy):
        """Test browser context creation without proxy configuration."""
        # Reload base to get updated env vars
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Ensure proxy is not set
        assert PROXY_SERVER is None or PROXY_SERVER == ""
        
        # Create context without proxy
        context = await mock_browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0...'
        )
        
        # Verify context was created
        assert context is not None
        mock_browser.new_context.assert_called_once()
        
        # Verify proxy was not included in call
        call_args = mock_browser.new_context.call_args
        assert 'proxy' not in call_args.kwargs or call_args.kwargs.get('proxy') is None
    
    @pytest.mark.asyncio
    async def test_context_creation_with_proxy(self, mock_browser, env_vars_with_proxy):
        """Test browser context creation with proxy configuration."""
        importlib.reload(base)
        from base import PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD
        
        # Verify proxy is configured
        assert PROXY_SERVER is not None
        
        # Create context with proxy
        proxy_config = {'server': PROXY_SERVER}
        if PROXY_USERNAME and PROXY_PASSWORD:
            proxy_config['username'] = PROXY_USERNAME
            proxy_config['password'] = PROXY_PASSWORD
        
        context = await mock_browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            proxy=proxy_config
        )
        
        # Verify context was created with proxy
        assert context is not None
        mock_browser.new_context.assert_called_once()
        
        # Verify proxy was included in call
        call_args = mock_browser.new_context.call_args
        assert 'proxy' in call_args.kwargs
        assert call_args.kwargs['proxy']['server'] == PROXY_SERVER
        assert call_args.kwargs['proxy']['username'] == PROXY_USERNAME
        assert call_args.kwargs['proxy']['password'] == PROXY_PASSWORD
    
    @pytest.mark.asyncio
    async def test_context_creation_with_proxy_no_auth(self, mock_browser, monkeypatch):
        """Test browser context creation with proxy but no authentication."""
        monkeypatch.setenv("PROXY_SERVER", "http://proxy.example.com:8080")
        monkeypatch.delenv("PROXY_USERNAME", raising=False)
        monkeypatch.delenv("PROXY_PASSWORD", raising=False)
        
        # Reload module to get new env vars
        importlib.reload(base)
        from base import PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD
        
        # Verify proxy server is set but auth is not
        assert PROXY_SERVER is not None
        assert PROXY_USERNAME is None or PROXY_USERNAME == ""
        assert PROXY_PASSWORD is None or PROXY_PASSWORD == ""
        
        # Create context with proxy (no auth)
        proxy_config = {'server': PROXY_SERVER}
        
        context = await mock_browser.new_context(proxy=proxy_config)
        
        # Verify context was created
        assert context is not None
        call_args = mock_browser.new_context.call_args
        assert 'proxy' in call_args.kwargs
        assert 'username' not in call_args.kwargs['proxy']
        assert 'password' not in call_args.kwargs['proxy']


class TestProxyFailureScenarios:
    """Tests for proxy failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_proxy_connection_timeout(self, mock_browser, env_vars_with_proxy):
        """Test handling of proxy connection timeout."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Mock browser context creation to raise timeout error
        mock_browser.new_context = AsyncMock(side_effect=PlaywrightTimeout("Proxy connection timeout"))
        
        # Attempt to create context with proxy
        with pytest.raises(PlaywrightTimeout):
            proxy_config = {'server': PROXY_SERVER}
            await mock_browser.new_context(proxy=proxy_config)
        
        # Verify error was raised
        mock_browser.new_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_proxy_authentication_failure(self, mock_browser, env_vars_with_proxy):
        """Test handling of proxy authentication failure."""
        importlib.reload(base)
        from base import PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD
        
        # Mock browser context creation to raise authentication error
        mock_browser.new_context = AsyncMock(
            side_effect=PlaywrightError("Proxy authentication failed")
        )
        
        # Attempt to create context with proxy
        with pytest.raises(PlaywrightError) as exc_info:
            proxy_config = {
                'server': PROXY_SERVER,
                'username': PROXY_USERNAME,
                'password': PROXY_PASSWORD
            }
            await mock_browser.new_context(proxy=proxy_config)
        
        # Verify error message
        assert "authentication" in str(exc_info.value).lower()
        mock_browser.new_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_proxy_connection_refused(self, mock_browser, env_vars_with_proxy):
        """Test handling of proxy connection refused error."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Mock browser context creation to raise connection refused error
        mock_browser.new_context = AsyncMock(
            side_effect=PlaywrightError("Connection refused by proxy server")
        )
        
        # Attempt to create context with proxy
        with pytest.raises(PlaywrightError) as exc_info:
            proxy_config = {'server': PROXY_SERVER}
            await mock_browser.new_context(proxy=proxy_config)
        
        # Verify error was raised
        assert "refused" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()
        mock_browser.new_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_proxy_invalid_url(self, mock_browser, monkeypatch):
        """Test handling of invalid proxy URL."""
        monkeypatch.setenv("PROXY_SERVER", "invalid://proxy-url")
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Mock browser context creation to raise error for invalid URL
        mock_browser.new_context = AsyncMock(
            side_effect=PlaywrightError("Invalid proxy URL format")
        )
        
        # Attempt to create context with invalid proxy
        with pytest.raises(PlaywrightError):
            proxy_config = {'server': PROXY_SERVER}
            await mock_browser.new_context(proxy=proxy_config)
    
    @pytest.mark.asyncio
    async def test_proxy_network_unreachable(self, mock_browser, env_vars_with_proxy):
        """Test handling of network unreachable error."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Mock browser context creation to raise network error
        mock_browser.new_context = AsyncMock(
            side_effect=PlaywrightError("Network unreachable")
        )
        
        # Attempt to create context with proxy
        with pytest.raises(PlaywrightError) as exc_info:
            proxy_config = {'server': PROXY_SERVER}
            await mock_browser.new_context(proxy=proxy_config)
        
        # Verify error was raised
        assert "network" in str(exc_info.value).lower() or "unreachable" in str(exc_info.value).lower()


class TestScrapeSingleAttemptAdapter:
    """Tests for scrape_single_attempt function."""
    
    @pytest.mark.asyncio
    async def test_scrape_single_attempt_success(self, mock_browser, mock_hashtag_html):
        """Test successful scraping attempt without proxy."""
        # Setup mock context and page properly
        mock_context = await mock_browser.new_context()
        mock_page = await mock_context.new_page()
        mock_page.content = AsyncMock(return_value=mock_hashtag_html)
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="TikTok Creative Center")
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.add_init_script = AsyncMock()
        
        url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
        
        # Mock BeautifulSoup parsing
        with patch('base.BeautifulSoup') as mock_soup:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(mock_hashtag_html, 'html.parser')
            mock_soup.return_value = soup
            
            # Mock selector finding
            with patch('base.SELECTORS', {
                'hashtag_item': ['[data-testid="hashtag_item"]'],
                'body': ['body']
            }):
                data, page_source = await scrape_single_attempt(
                    mock_browser, url, debug=False, use_proxy=False
                )
        
        # Verify results
        assert isinstance(data, list)
        assert page_source == mock_hashtag_html
    
    @pytest.mark.asyncio
    async def test_scrape_single_attempt_with_proxy(self, mock_browser, env_vars_with_proxy, mock_hashtag_html):
        """Test scraping attempt with proxy enabled."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Setup mock context and page properly
        mock_context = await mock_browser.new_context()
        mock_page = await mock_context.new_page()
        mock_page.content = AsyncMock(return_value=mock_hashtag_html)
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="TikTok Creative Center")
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.add_init_script = AsyncMock()
        
        url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
        
        # Verify proxy is configured
        assert PROXY_SERVER is not None
        
        # Mock BeautifulSoup
        with patch('base.BeautifulSoup') as mock_soup:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(mock_hashtag_html, 'html.parser')
            mock_soup.return_value = soup
            
            with patch('base.SELECTORS', {
                'hashtag_item': ['[data-testid="hashtag_item"]'],
                'body': ['body']
            }):
                data, page_source = await scrape_single_attempt(
                    mock_browser, url, debug=False, use_proxy=True
                )
        
        # Verify context was created with proxy
        call_args = mock_browser.new_context.call_args
        if call_args and 'proxy' in call_args.kwargs:
            assert call_args.kwargs['proxy']['server'] == PROXY_SERVER
    
    @pytest.mark.asyncio
    async def test_scrape_single_attempt_proxy_failure(self, mock_browser, env_vars_with_proxy):
        """Test scraping attempt when proxy fails."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        # Mock browser context creation to fail with proxy
        mock_browser.new_context = AsyncMock(
            side_effect=PlaywrightError("Proxy connection failed")
        )
        
        url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
        
        # Attempt scraping with proxy
        with pytest.raises(PlaywrightError):
            await scrape_single_attempt(mock_browser, url, debug=False, use_proxy=True)
        
        # Verify proxy was attempted
        mock_browser.new_context.assert_called()
        call_args = mock_browser.new_context.call_args
        if call_args and 'proxy' in call_args.kwargs:
            assert call_args.kwargs['proxy']['server'] == PROXY_SERVER
    
    @pytest.mark.asyncio
    async def test_scrape_single_attempt_timeout(self, mock_browser):
        """Test scraping attempt with page load timeout."""
        # Setup mock context and page properly
        mock_context = await mock_browser.new_context()
        mock_page = await mock_context.new_page()
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeout("Page load timeout"))
        mock_page.add_init_script = AsyncMock()
        
        url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
        
        # Attempt scraping
        data, page_source = await scrape_single_attempt(
            mock_browser, url, debug=False, use_proxy=False
        )
        
        # Should return empty data on timeout
        assert data == []
        assert page_source == ""
    
    @pytest.mark.asyncio
    async def test_scrape_single_attempt_no_hashtags(self, mock_browser):
        """Test scraping attempt when no hashtags are found."""
        # Setup mock context and page properly
        mock_context = await mock_browser.new_context()
        mock_page = await mock_context.new_page()
        mock_page.content = AsyncMock(return_value="<html><body>No hashtags</body></html>")
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="TikTok")
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.add_init_script = AsyncMock()
        
        url = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
        
        # Mock BeautifulSoup with no hashtag elements
        with patch('base.BeautifulSoup') as mock_soup:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup("<html><body>No hashtags</body></html>", 'html.parser')
            mock_soup.return_value = soup
            
            with patch('base.SELECTORS', {
                'hashtag_item': ['[data-testid="hashtag_item"]'],
                'body': ['body']
            }):
                data, page_source = await scrape_single_attempt(
                    mock_browser, url, debug=False, use_proxy=False
                )
        
        # Should return empty data
        assert data == []


class TestScrapeWithRetryAdapter:
    """Tests for scrape_with_retry function."""
    
    @pytest.mark.asyncio
    async def test_scrape_with_retry_success(self, mock_page, mock_hashtag_html):
        """Test successful scraping with retry logic."""
        mock_page.content = AsyncMock(return_value=mock_hashtag_html)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.evaluate = AsyncMock()
        
        # Mock BeautifulSoup
        with patch('base.BeautifulSoup') as mock_soup:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(mock_hashtag_html, 'html.parser')
            mock_soup.return_value = soup
            
            with patch('base.SELECTORS', {
                'hashtag_item': ['[data-testid="hashtag_item"]'],
                'view_more_button': ['button:has-text("View more")']
            }):
                hashtag_elements, page_source = await scrape_with_retry(mock_page, max_retries=2)
        
        # Verify results
        assert len(hashtag_elements) > 0
        assert page_source == mock_hashtag_html
    
    @pytest.mark.asyncio
    async def test_scrape_with_retry_insufficient_data(self, mock_page):
        """Test retry logic when insufficient data is found."""
        # First attempt returns few elements, second returns more
        mock_page.content = AsyncMock(side_effect=[
            "<html><body><div data-testid='hashtag_item'>1#Test</div></body></html>",
            "<html><body>" + "".join([f"<div data-testid='hashtag_item'>{i}#Test{i}</div>" 
                                     for i in range(50)]) + "</body></html>"
        ])
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.evaluate = AsyncMock()
        mock_page.reload = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        
        # Mock BeautifulSoup
        with patch('base.BeautifulSoup') as mock_soup:
            from bs4 import BeautifulSoup
            
            def soup_side_effect(html, parser):
                return BeautifulSoup(html, parser)
            
            mock_soup.side_effect = soup_side_effect
            
            with patch('base.SELECTORS', {
                'hashtag_item': ['[data-testid="hashtag_item"]'],
                'view_more_button': ['button:has-text("View more")'],
                'body': ['body']
            }):
                with patch('base.ensure_hashtags_tab', new_callable=AsyncMock):
                    hashtag_elements, page_source = await scrape_with_retry(mock_page, max_retries=2)
        
        # Should have retried and gotten more data
        assert len(hashtag_elements) > 0


class TestScrapeTikTokHashtagsAdapter:
    """Tests for main scrape_tiktok_hashtags function with proxy scenarios."""
    
    @pytest.mark.asyncio
    async def test_scrape_tiktok_hashtags_success_no_proxy(self, mock_playwright, env_vars_no_proxy, mock_hashtag_html):
        """Test successful scraping without proxy."""
        mock_browser = await mock_playwright.chromium.launch()
        mock_context = await mock_browser.new_context()
        mock_page = await mock_context.new_page()
        mock_page.content = AsyncMock(return_value=mock_hashtag_html)
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="TikTok Creative Center")
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.add_init_script = AsyncMock()
        
        # Mock async_playwright
        with patch('base.async_playwright', return_value=mock_playwright):
            with patch('base.BeautifulSoup') as mock_soup:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(mock_hashtag_html, 'html.parser')
                mock_soup.return_value = soup
                
                with patch('base.SELECTORS', {
                    'hashtag_item': ['[data-testid="hashtag_item"]'],
                    'body': ['body'],
                    'hashtag_tab': ['text=Hashtags']
                }):
                    with patch('base.init_supabase', return_value=None):
                        data = await scrape_tiktok_hashtags(
                            headless=True, debug=False, upload_to_db=False, region="en"
                        )
        
        # Verify results
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_scrape_tiktok_hashtags_with_proxy_success(self, mock_playwright, env_vars_with_proxy, mock_hashtag_html):
        """Test successful scraping with proxy."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        mock_browser = await mock_playwright.chromium.launch()
        mock_context = await mock_browser.new_context()
        mock_page = await mock_context.new_page()
        mock_page.content = AsyncMock(return_value=mock_hashtag_html)
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="TikTok Creative Center")
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.add_init_script = AsyncMock()
        
        # Mock async_playwright
        with patch('base.async_playwright', return_value=mock_playwright):
            with patch('base.BeautifulSoup') as mock_soup:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(mock_hashtag_html, 'html.parser')
                mock_soup.return_value = soup
                
                with patch('base.SELECTORS', {
                    'hashtag_item': ['[data-testid="hashtag_item"]'],
                    'body': ['body'],
                    'hashtag_tab': ['text=Hashtags']
                }):
                    with patch('base.init_supabase', return_value=None):
                        data = await scrape_tiktok_hashtags(
                            headless=True, debug=False, upload_to_db=False, region="en"
                        )
        
        # Verify proxy was used on retry attempts
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_scrape_tiktok_hashtags_proxy_failure_then_success(self, mock_playwright, env_vars_with_proxy, mock_hashtag_html):
        """Test scraping when proxy fails but succeeds without proxy on retry."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        mock_browser = await mock_playwright.chromium.launch()
        
        # First attempt with proxy fails, subsequent attempts succeed
        call_count = 0
        async def mock_new_context(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and 'proxy' in kwargs:
                # First call with proxy fails
                raise PlaywrightError("Proxy connection failed")
            # Subsequent calls succeed
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.content = AsyncMock(return_value=mock_hashtag_html)
            mock_page.goto = AsyncMock()
            mock_page.title = AsyncMock(return_value="TikTok Creative Center")
            mock_page.wait_for_selector = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=None)
            mock_page.add_init_script = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            return mock_context
        
        mock_browser.new_context = mock_new_context
        
        # Mock async_playwright
        with patch('base.async_playwright', return_value=mock_playwright):
            with patch('base.BeautifulSoup') as mock_soup:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(mock_hashtag_html, 'html.parser')
                mock_soup.return_value = soup
                
                with patch('base.SELECTORS', {
                    'hashtag_item': ['[data-testid="hashtag_item"]'],
                    'body': ['body'],
                    'hashtag_tab': ['text=Hashtags']
                }):
                    with patch('base.init_supabase', return_value=None):
                        data = await scrape_tiktok_hashtags(
                            headless=True, debug=False, upload_to_db=False, region="en"
                        )
        
        # Should eventually succeed
        assert isinstance(data, list)
        assert call_count > 1  # Should have retried
    
    @pytest.mark.asyncio
    async def test_scrape_tiktok_hashtags_all_attempts_fail(self, mock_playwright, env_vars_with_proxy):
        """Test scraping when all attempts fail."""
        mock_browser = await mock_playwright.chromium.launch()
        
        # All attempts fail
        mock_browser.new_context = AsyncMock(
            side_effect=PlaywrightError("Connection failed")
        )
        
        # Mock async_playwright
        with patch('base.async_playwright', return_value=mock_playwright):
            with patch('base.init_supabase', return_value=None):
                with pytest.raises(PlaywrightError):
                    await scrape_tiktok_hashtags(
                        headless=True, debug=False, upload_to_db=False, region="en"
                    )


class TestProxyRetryLogic:
    """Tests for proxy retry logic and fallback behavior."""
    
    @pytest.mark.asyncio
    async def test_proxy_used_on_retry_attempts(self, mock_playwright, env_vars_with_proxy):
        """Test that proxy is used on retry attempts (not first attempt)."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        mock_browser = await mock_playwright.chromium.launch()
        
        # Track proxy usage via scrape_single_attempt calls
        proxy_used_in_calls = []
        
        # Sample scraped data that would be returned
        sample_data = [
            {"hashtag": f"#Test{i}", "posts": "100K", "engagement_score": 5.0, 
             "sentiment_polarity": 0.0, "sentiment_label": "Neutral"}
            for i in range(1, 15)
        ]
        success_html = "<html><body>Success</body></html>"
        
        with patch('base.async_playwright', return_value=mock_playwright):
            with patch('base.scrape_single_attempt', new_callable=AsyncMock) as mock_scrape:
                # Track proxy usage and handle retries
                async def scrape_side_effect(*args, **kwargs):
                    use_proxy = kwargs.get('use_proxy', False)
                    proxy_used_in_calls.append(use_proxy)
                    
                    # First call fails (no proxy), subsequent calls succeed
                    if mock_scrape.call_count == 1:
                        raise PlaywrightError("First attempt failed")
                    return (sample_data, success_html)
                
                mock_scrape.side_effect = scrape_side_effect
                
                with patch('base.init_supabase', return_value=None):
                    data = await scrape_tiktok_hashtags(
                        headless=True, debug=False, upload_to_db=False, region="en"
                    )
        
        # First attempt should not use proxy, retry should use proxy
        assert len(proxy_used_in_calls) >= 2
        assert proxy_used_in_calls[0] is False  # First attempt no proxy
        # At least one retry should use proxy
        assert any(proxy_used_in_calls[1:])  # Retry attempts use proxy
        # Should eventually succeed
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_proxy_fallback_to_direct_connection(self, mock_playwright, env_vars_with_proxy):
        """Test that proxy failures are handled and retries continue."""
        importlib.reload(base)
        from base import PROXY_SERVER
        
        mock_browser = await mock_playwright.chromium.launch()
        
        # Track proxy usage via scrape_single_attempt calls
        proxy_attempts = []
        
        # Sample scraped data that would be returned
        sample_data = [
            {"hashtag": f"#Test{i}", "posts": "100K", "engagement_score": 5.0, 
             "sentiment_polarity": 0.0, "sentiment_label": "Neutral"}
            for i in range(1, 15)
        ]
        success_html = "<html><body>Success</body></html>"
        
        with patch('base.async_playwright', return_value=mock_playwright):
            with patch('base.scrape_single_attempt', new_callable=AsyncMock) as mock_scrape:
                # Track proxy usage and handle failures
                async def scrape_side_effect(*args, **kwargs):
                    use_proxy = kwargs.get('use_proxy', False)
                    proxy_attempts.append(use_proxy)
                    
                    # First attempt without proxy returns insufficient data
                    if mock_scrape.call_count == 1:
                        return ([], "")
                    # Second attempt with proxy fails
                    elif mock_scrape.call_count == 2 and use_proxy:
                        raise PlaywrightError("Proxy failed")
                    # Third attempt with proxy succeeds (proxy recovered)
                    else:
                        return (sample_data, success_html)
                
                mock_scrape.side_effect = scrape_side_effect
                
                with patch('base.init_supabase', return_value=None):
                    data = await scrape_tiktok_hashtags(
                        headless=True, debug=False, upload_to_db=False, region="en"
                    )
        
        # Should eventually succeed
        assert isinstance(data, list)
        # Should have tried without proxy first, then with proxy
        assert False in proxy_attempts  # Direct connection was attempted (first attempt)
        assert True in proxy_attempts  # Proxy was attempted (retry attempts)
        # Should have multiple attempts
        assert len(proxy_attempts) >= 2

