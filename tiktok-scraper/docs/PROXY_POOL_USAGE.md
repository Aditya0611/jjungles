# Proxy Pool Usage Guide

## Overview

The proxy pool abstraction provides:
- **Proxy Rotation**: Automatic rotation with multiple strategies
- **Health Scoring**: Success/failure tracking and health-based selection
- **Retry/Backoff**: Exponential backoff for failed proxies
- **Circuit Breaker**: Automatic isolation of failing proxies

## Features

### 1. Proxy Rotation Strategies

- **`weighted_random`** (default): Selects proxies based on health scores (healthier proxies more likely)
- **`round_robin`**: Cycles through proxies in order
- **`health_only`**: Always selects the healthiest available proxy

### 2. Health Scoring

Health score (0.0 to 1.0) considers:
- **Success Rate** (60% weight): Percentage of successful requests
- **Recency** (20% weight): Time since last success
- **Response Time** (20% weight): Average response time
- **Circuit Breaker Penalty**: Heavy penalty for open circuits

### 3. Circuit Breaker

- Opens after **5 consecutive failures** (configurable)
- **5-minute cooldown** before attempting recovery
- Half-open state for testing recovery
- Automatic closure on successful request

### 4. Exponential Backoff

- Base backoff: 1 minute
- Doubles with each consecutive failure
- Capped at 32 minutes
- Automatic reset on success

## Configuration

### Environment Variables

#### Single Proxy (Backward Compatible)
```bash
export PROXY_SERVER="http://proxy.example.com:8080"
export PROXY_USERNAME="username"
export PROXY_PASSWORD="password"
```

#### Multiple Proxies
```bash
# Comma-separated list
export PROXY_LIST="http://proxy1.com:8080,http://proxy2.com:8080,http://proxy3.com:8080"

# Or with authentication (format: http://user:pass@host:port)
export PROXY_LIST="http://user1:pass1@proxy1.com:8080,http://user2:pass2@proxy2.com:8080"
```

### Programmatic Configuration

```python
from proxy_pool import ProxyPool, ProxyConfig

# Create proxy configurations
proxies = [
    ProxyConfig(
        server="http://proxy1.example.com:8080",
        username="user1",
        password="pass1",
        region="us-east",
        tags=["residential", "premium"]
    ),
    ProxyConfig(
        server="http://proxy2.example.com:8080",
        username="user2",
        password="pass2",
        region="us-west",
        tags=["datacenter", "premium"]
    ),
]

# Create pool
proxy_pool = ProxyPool(
    proxies=proxies,
    rotation_strategy="weighted_random",  # or "round_robin", "health_only"
    min_health_score=0.3,  # Minimum health to use proxy
    max_concurrent_per_proxy=3,  # Max concurrent requests per proxy
    enable_circuit_breaker=True,
)
```

## Usage

### Basic Usage

```python
from proxy_pool import ProxyPool, ProxyConfig, use_proxy

# Initialize pool
proxy_pool = ProxyPool(proxies=[...])

# Get a proxy
proxy = proxy_pool.get_proxy()
if proxy:
    # Use proxy with Playwright
    context = await browser.new_context(proxy=proxy.to_playwright_config())
    # ... do work ...
    proxy_pool.record_success(proxy)
else:
    # No proxy available
    pass
```

### Context Manager (Recommended)

```python
async with use_proxy(proxy_pool, max_retries=3) as proxy:
    if proxy:
        context = await browser.new_context(proxy=proxy.to_playwright_config())
        page = await context.new_page()
        await page.goto("https://example.com")
        # Success automatically recorded
        proxy_pool.record_success(proxy)
    else:
        # Handle no proxy available
        pass
```

### With Error Handling

```python
from proxy_pool import use_proxy
from logging_metrics import log_error

async with use_proxy(proxy_pool) as proxy:
    if not proxy:
        raise Exception("No proxy available")
    
    try:
        context = await browser.new_context(proxy=proxy.to_playwright_config())
        page = await context.new_page()
        await page.goto("https://example.com")
        proxy_pool.record_success(proxy)
    except Exception as e:
        # Record failure with error category
        error_category = "network" if "network" in str(e).lower() else "unknown"
        proxy_pool.record_failure(proxy, error_category=error_category)
        raise
```

### Filtering by Tags

```python
# Get proxy with specific tags
proxy = proxy_pool.get_proxy(tags=["residential", "premium"])

# Exclude specific proxies
excluded = ["http://bad-proxy.com:8080"]
proxy = proxy_pool.get_proxy(exclude_proxies=excluded)
```

## Monitoring

### Get Proxy Health

```python
# Get health for all proxies
health_data = proxy_pool.get_all_proxy_health()
for proxy_key, health in health_data.items():
    print(f"{proxy_key}:")
    print(f"  Health Score: {health['health_score']:.2f}")
    print(f"  Success Rate: {health['success_rate']:.2%}")
    print(f"  State: {health['state']}")
    print(f"  Total Requests: {health['total_requests']}")
```

### Get Pool Metrics

```python
metrics = proxy_pool.get_metrics()
print(f"Total Proxies: {metrics['total_proxies']}")
print(f"Available Proxies: {metrics['available_proxies']}")
print(f"Active Requests: {metrics['active_requests']}")
print(f"Proxy Selections: {metrics['proxy_selections_total']}")
print(f"Successes: {metrics['proxy_successes_total']}")
print(f"Failures: {metrics['proxy_failures_total']}")
print(f"Circuit Breaker Opens: {metrics['circuit_breaker_opens_total']}")
```

## Integration with Metrics

The proxy pool integrates with the metrics system:

```python
from logging_metrics import metrics

# Metrics are automatically tracked:
# - proxy_selections_total
# - proxy_successes_total
# - proxy_failures_total
# - circuit_breaker_opens_total

# Get metrics
all_metrics = metrics.get_all_metrics()
```

## Best Practices

### 1. Proxy Selection Strategy

- **Production**: Use `weighted_random` for load distribution
- **Testing**: Use `health_only` to always use best proxy
- **Load Balancing**: Use `round_robin` for even distribution

### 2. Health Score Threshold

- **Conservative**: `min_health_score=0.5` (only healthy proxies)
- **Balanced**: `min_health_score=0.3` (default, allows some risk)
- **Aggressive**: `min_health_score=0.1` (use even poor proxies)

### 3. Concurrent Requests

- Set `max_concurrent_per_proxy` based on proxy provider limits
- Typical values: 1-5 concurrent requests per proxy

### 4. Circuit Breaker Configuration

- **Failure Threshold**: 5 consecutive failures (default)
- **Cooldown**: 5 minutes (default)
- Adjust based on proxy reliability

### 5. Error Categories

Use specific error categories for better tracking:
- `"network"`: Network/connection errors
- `"timeout"`: Timeout errors
- `"authentication"`: Auth failures
- `"rate_limit"`: Rate limiting
- `"proxy"`: Proxy-specific errors

## Example: Full Integration

```python
import asyncio
from playwright.async_api import async_playwright
from proxy_pool import ProxyPool, ProxyConfig, use_proxy
from logging_metrics import trace_request, log_error

# Initialize pool
proxies = [
    ProxyConfig(server="http://proxy1.com:8080", username="user1", password="pass1"),
    ProxyConfig(server="http://proxy2.com:8080", username="user2", password="pass2"),
]
proxy_pool = ProxyPool(proxies=proxies)

async def scrape_with_proxy(url: str):
    with trace_request("scrape_with_proxy") as trace:
        async with use_proxy(proxy_pool) as proxy:
            if not proxy:
                raise Exception("No proxy available")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context(proxy=proxy.to_playwright_config())
                page = await context.new_page()
                
                try:
                    await page.goto(url)
                    content = await page.content()
                    proxy_pool.record_success(proxy)
                    return content
                except Exception as e:
                    error_category = "network" if "network" in str(e).lower() else "unknown"
                    proxy_pool.record_failure(proxy, error_category=error_category)
                    log_error(e, context={"url": url, "proxy": proxy.server})
                    raise
                finally:
                    await browser.close()

# Run
asyncio.run(scrape_with_proxy("https://example.com"))
```

## Troubleshooting

### No Proxies Available

- Check proxy health scores: `proxy_pool.get_all_proxy_health()`
- Lower `min_health_score` threshold
- Check circuit breaker state
- Verify proxies are not in backoff period

### All Proxies Failing

- Check proxy credentials
- Verify proxy servers are accessible
- Check network connectivity
- Review error categories in logs

### Circuit Breaker Always Open

- Proxies may be permanently failing
- Check proxy provider status
- Verify credentials
- Consider removing bad proxies from pool

## Advanced Features

### Manual Proxy Reset

```python
# Reset a proxy's health (for testing/recovery)
proxy_pool.reset_proxy(proxy_config)
```

### Dynamic Proxy Management

```python
# Add proxy at runtime
new_proxy = ProxyConfig(server="http://new-proxy.com:8080")
proxy_pool.add_proxy(new_proxy)

# Remove proxy
proxy_pool.remove_proxy(bad_proxy)
```

### Custom Health Scoring

Modify `ProxyHealth.get_health_score()` to customize scoring algorithm.

---

**Status**: ✅ Production Ready
**Integration**: Fully integrated with `base.py` and `logging_metrics.py`

