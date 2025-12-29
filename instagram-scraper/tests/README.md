# Instagram Scraper Unit Tests

This directory contains comprehensive unit tests for all scraper adapters, including proxy failure scenarios.

## Test Structure

```
tests/
├── __init__.py                    # Test package initialization
├── conftest.py                    # Shared pytest fixtures
├── test_engagement_scraper.py     # Tests for engagement extraction
├── test_hashtag_discovery.py      # Tests for hashtag discovery
├── test_hashtag_engagement.py     # Tests for engagement analysis
└── test_proxy_scenarios.py         # Tests for proxy failure scenarios
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-mock pytest-cov
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_engagement_scraper.py
```

### Run with Coverage

```bash
pytest tests/ --cov=main --cov-report=html
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

## Test Coverage

### Engagement Scraper (`test_engagement_scraper.py`)

- ✅ Successful engagement extraction (likes, comments, views)
- ✅ Photo post engagement extraction
- ✅ Reel/video post engagement extraction
- ✅ Proxy connection failure handling
- ✅ Proxy timeout handling
- ✅ Proxy authentication failure handling
- ✅ Network error handling
- ✅ Missing engagement data fallback
- ✅ Content type detection
- ✅ Caption extraction
- ✅ K/M suffix parsing (5.2K, 1.2M)

### Hashtag Discovery (`test_hashtag_discovery.py`)

- ✅ Successful hashtag discovery
- ✅ Proxy failure on explore page
- ✅ Proxy timeout during navigation
- ✅ Network error handling
- ✅ No hashtags found scenario
- ✅ Hashtag frequency calculation
- ✅ Hashtag categorization
- ✅ Sample posts extraction

### Hashtag Engagement Analysis (`test_hashtag_engagement.py`)

- ✅ Successful engagement analysis
- ✅ Proxy failure during post analysis
- ✅ Proxy timeout handling
- ✅ No sample posts fallback
- ✅ Sentiment aggregation across posts
- ✅ Language aggregation
- ✅ Content type distribution
- ✅ Engagement averaging

### Proxy Failure Scenarios (`test_proxy_scenarios.py`)

- ✅ Connection refused errors
- ✅ Timeout errors
- ✅ Authentication failures
- ✅ Intermittent proxy failures
- ✅ Retry logic validation
- ✅ Graceful degradation
- ✅ Error logging
- ✅ Full pipeline proxy failures

## Fixtures

All fixtures are defined in `conftest.py`:

### Mock Objects
- `mock_page` - Basic Playwright page mock
- `mock_page_with_engagement` - Page with engagement data
- `mock_page_with_hashtags` - Page with hashtag data
- `mock_supabase_client` - Mock Supabase client

### Proxy Configurations
- `proxy_config` - Standard HTTP proxy with auth
- `proxy_config_no_auth` - HTTP proxy without auth
- `proxy_config_socks5` - SOCKS5 proxy configuration

### Proxy Failure Scenarios
- `proxy_failure_page` - Simulates connection refused
- `proxy_timeout_page` - Simulates timeout
- `proxy_auth_failure_page` - Simulates auth failure
- `network_error_page` - Simulates general network errors

### Sample Data
- `sample_engagement_data` - Sample post engagement data
- `sample_hashtag_data` - Sample hashtag discovery data
- `sample_trend_summary` - Sample trend aggregation
- `sample_post_urls` - Sample Instagram post URLs

### Configuration
- `mock_config` - Mocked environment variables

## Writing New Tests

### Example Test Structure

```python
import pytest
from unittest.mock import patch, MagicMock
from main import your_function

class TestYourAdapter:
    """Test suite for your adapter."""
    
    def test_successful_operation(self, mock_page):
        """Test successful operation."""
        with patch('main.time.sleep'), patch('main.logger'):
            result = your_function(mock_page, "input")
        
        assert result is not None
        assert 'expected_key' in result
    
    def test_proxy_failure(self, proxy_failure_page):
        """Test proxy failure handling."""
        with patch('main.time.sleep'), patch('main.logger'):
            result = your_function(proxy_failure_page, "input")
        
        assert isinstance(result, dict)  # Should handle gracefully
```

### Best Practices

1. **Always mock time.sleep** - Tests should run fast
2. **Mock logger** - Avoid cluttering test output
3. **Use fixtures** - Reuse common mock objects
4. **Test both success and failure paths** - Especially proxy failures
5. **Assert expected structure** - Verify return types and keys
6. **Test edge cases** - Empty data, missing fields, etc.

## Continuous Integration

Tests are designed to run in CI/CD pipelines. They:
- Don't require actual Instagram access
- Don't require real proxy servers
- Use mocks for all external dependencies
- Complete in seconds

## Troubleshooting

### Import Errors

If you get import errors, ensure the parent directory is in Python path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Mock Not Working

Ensure you're patching the correct module path:
- Use `'main.function_name'` not `'function_name'`
- Patch where the function is used, not where it's defined

### Proxy Tests Failing

Proxy failure tests use custom exceptions (`ProxyError`, `ProxyTimeoutError`). 
Ensure these are imported from `tests.conftest`.

