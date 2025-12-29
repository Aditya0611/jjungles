# Scraper Adapter Tests

Comprehensive unit tests for scraper adapters with proxy failure scenarios.

## ✅ Status

All 21 tests are successfully configured and ready to run!

## Quick Start

```bash
# Run all tests
python -m pytest tests\test_scraper_adapters.py -v

# Run specific test class
python -m pytest tests\test_scraper_adapters.py::TestProxyFailureScenarios -v

# Run with coverage
python -m pytest tests\test_scraper_adapters.py --cov=base --cov-report=html
```

## Test Coverage

- **21 tests** covering all scraper adapters
- **6 test classes** organized by functionality
- **Proxy failure scenarios** comprehensively tested
- **Async support** properly configured with pytest-asyncio

## Dependencies

- `pytest>=8.0.0`
- `pytest-asyncio>=1.3.0` (installed)
- `pytest-mock>=3.15.0` (installed)

## Configuration

The `pytest.ini` file configures:
- `asyncio_mode = auto` - Automatically handles async tests
- Test discovery patterns
- Output formatting

All tests are properly marked with `@pytest.mark.asyncio` and will run automatically.

