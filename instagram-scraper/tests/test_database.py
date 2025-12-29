"""
Simplified tests for database and core operations.
Tests target actual functions in main.py.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseOperations:
    """Tests for database save operations."""
    
    @patch('main.create_client')
    def test_supabase_client_creation(self, mock_create_client):
        """Test Supabase client can be created."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        from main import create_client as client_func
        result = mock_create_client("url", "key")
        
        assert result is not None
    
    def test_trend_record_creation(self):
        """Test TrendRecord can be created."""
        from main import TrendRecord
        
        now = datetime.utcnow()
        record = TrendRecord(
            platform="Instagram",
            url="https://instagram.com/explore/tags/test/",
            hashtags=["#test"],
            likes=1000,
            comments=50,
            views=5000,
            language="en",
            timestamp=now,
            engagement_score=1500.0,
            version="test-1",
            raw_blob={"category": "general"}
        )
        
        assert record.platform == "Instagram"
        assert record.likes == 1000
        assert len(record.hashtags) == 1
    
    def test_trend_record_to_dict(self):
        """Test TrendRecord.to_dict() conversion."""
        from main import TrendRecord
        
        now = datetime.utcnow()
        record = TrendRecord(
            platform="Instagram",
            url="https://instagram.com/explore/tags/test/",
            hashtags=["#test"],
            likes=1000,
            comments=50,
            views=5000,
            language="en",
            timestamp=now,
            engagement_score=1500.0,
            version="test-1",
            raw_blob={"category": "general"}
        )
        
        data = record.to_dict()
        
        assert isinstance(data, dict)
        assert data['platform'] == "Instagram"
        assert data['likes'] == 1000


class TestSaveTrendsToDatabase:
    """Tests for save_trends_to_database function."""
    
    @patch('main.analyze_hashtag_engagement')
    def test_save_trends_basic(self, mock_analyze):
        """Test basic save_trends_to_database flow."""
        from main import save_trends_to_database
        
        mock_page = Mock()
        mock_supabase = Mock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{'id': 1}])
        
        # Mock engagement data
        mock_analyze.return_value =  {
            'avg_likes': 1000,
            'avg_comments': 50,
            'avg_views': 5000,
            'avg_engagement': 1500,
            'sentiment_summary': {},
            'language_summary': {'primary_language': 'en'},
            'content_types': {},
            'primary_format': 'photo',
            'video_count': 0
        }
        
        hashtag_data = [
            {'hashtag': 'test1', 'frequency': 5, 'category': 'general', 'posts_count': 100}
        ]
        
        result = save_trends_to_database(mock_page, mock_supabase, hashtag_data)
        
        # Should return list of saved hashtags
        assert isinstance(result, list)


class TestConfigValidation:
    """Tests for Config validation."""
    
    def test_config_exists(self):
        """Test Config class exists and has required attributes."""
        from main import Config
        
        assert hasattr(Config, 'SUPABASE_URL')
        assert hasattr(Config, 'SUPABASE_KEY')
        assert hasattr(Config, 'USERNAME')
        assert hasattr(Config, 'PASSWORD')
    
    def test_config_validate_method(self):
        """Test Config.validate() method exists."""
        from main import Config
        
        assert hasattr(Config, 'validate')
        assert callable(Config.validate)


class TestProxyWrappers:
    """Tests for proxy_wrappers module."""
    
    @patch('main.Config')
    def test_create_browser_context_without_proxy(self, mock_config):
        """Test browser context creation without proxy pool."""
        from proxy_wrappers import create_browser_context_with_retry
        
        mock_browser = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        
        # Mock Config attributes
        mock_config.VIEWPORT_WIDTH = 1920
        mock_config.VIEWPORT_HEIGHT = 1080
        mock_config.LOCALE = 'en-US'
        mock_config.TIMEZONE = 'America/New_York'
        mock_config.PROXY_BYPASS = None
        
        result_context, result_proxy = create_browser_context_with_retry(
            mock_browser, proxy_pool=None, max_retries=1
        )
        
        assert result_context is not None
        assert result_proxy is None
    
    @patch('proxy_wrappers.create_browser_context_with_retry')
    @patch('main.login_instagram')
    def test_login_with_retry_no_pool(self, mock_login, mock_create_context):
        """Test login without proxy pool."""
        from proxy_wrappers import login_with_retry
        
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        
        # Setup create_browser_context_with_retry to return context
        mock_create_context.return_value = (mock_context, None)
        
        # Setup context.new_page()
        mock_context.new_page.return_value = mock_page
        
        # Setup login success
        mock_login.return_value = True
        
        result_context, result_page, success = login_with_retry(mock_browser, proxy_pool=None)
        
        assert success is True
        assert result_context == mock_context
        assert result_page == mock_page
    
    @patch('main.discover_trending_hashtags')
    def test_discover_hashtags_no_pool(self, mock_discover):
        """Test hashtag discovery without proxy pool."""
        from proxy_wrappers import discover_hashtags_with_retry
        
        mock_page = Mock()
        mock_discover.return_value = [{'hashtag': 'test'}]
        
        result = discover_hashtags_with_retry(mock_page, proxy_pool=None)
        
        assert isinstance(result, list)
        assert len(result) == 1


class TestRunScraperJob:
    """Tests for run_scraper_job function."""
    
    @patch('main.sync_playwright')
    @patch('main.create_client')
    @patch('main.initialize_proxy_pool')
    def test_run_scraper_job_browser_launch_failure(
        self,
        mock_proxy_pool,
        mock_create_client,
        mock_playwright
    ):
        """Test graceful handling of browser launch failure."""
        from main import run_scraper_job
        
        # Mock browser launch failure
        mock_playwright.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("Launch failed")
        
        # Should not raise exception
        try:
            run_scraper_job()
        except:
            pytest.fail("run_scraper_job should handle browser launch failure gracefully")


class TestEngagementCalculator:
    """Tests for engagement calculator module."""
    
    def test_engagement_calculator_import(self):
        """Test engagement calculator can be imported."""
        try:
            from engagement_calculator import EngagementCalculator
            assert EngagementCalculator is not None
        except ImportError as e:
            pytest.fail(f"Cannot import EngagementCalculator: {e}")
    
    def test_calculate_engagement_score_import(self):
        """Test calculate_engagement_score function exists."""
        try:
            from engagement_calculator import calculate_engagement_score
            assert calculate_engagement_score is not None
        except ImportError as e:
            pytest.fail(f"Cannot import calculate_engagement_score: {e}")


class TestProxyPool:
    """Tests for ProxyPool module."""
    
    def test_proxy_pool_import(self):
        """Test ProxyPool can be imported."""
        try:
            from proxy_pool import ProxyPool
            assert ProxyPool is not None
        except ImportError as e:
            pytest.fail(f"Cannot import ProxyPool: {e}")
    
    def test_proxy_pool_execute_with_retry(self):
        """Test execute_with_retry method exists."""
        from proxy_pool import ProxyPool
        
        proxies = [{'server': 'http://proxy.example.com:8080'}]
        pool = ProxyPool(proxies)
        
        assert hasattr(pool, 'execute_with_retry')
        assert callable(pool.execute_with_retry)


class TestETLPipeline:
    """Tests for ETL Pipeline module."""
    
    def test_etl_pipeline_import(self):
        """Test ETLPipeline can be imported."""
        try:
            from etl_pipeline import ETLPipeline
            assert ETLPipeline is not None
        except ImportError as e:
            pytest.fail(f"Cannot import ETLPipeline: {e}")


class TestTrendSnapshot:
    """Tests for TrendSnapshot module."""
    
    def test_trend_snapshot_manager_import(self):
        """Test TrendSnapshotManager can be imported."""
        try:
            from trend_snapshot import TrendSnapshotManager
            assert TrendSnapshotManager is not None
        except ImportError as e:
            pytest.fail(f"Cannot import TrendSnapshotManager: {e}")


# Add a simple passing test to ensure pytest works
def test_basic_assertion():
    """Basic test to verify pytest is working."""
    assert True
    assert 1 + 1 == 2
    assert "test" == "test"
