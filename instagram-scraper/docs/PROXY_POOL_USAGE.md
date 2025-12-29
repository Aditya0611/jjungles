# Proxy Pool Usage Guide

## Overview

The proxy pool system provides robust proxy management with:
- **Automatic Rotation**: Health-based, round-robin, or random
- **Health Scoring**: Tracks success/failure rates and latency
- **Retry with Backoff**: Exponential backoff on failures
- **Circuit Breaker**: Prevents using repeatedly failed proxies

## Configuration

### Environment Variables

```bash
# Single proxy (backward compatible)
PROXY_SERVER=http://proxy1.example.com:8080
PROXY_USERNAME=user1
PROXY_PASSWORD=pass1

# Multiple proxies (comma-separated)
PROXY_SERVERS=http://proxy1.example.com:8080,http://proxy2.example.com:8080,socks5://proxy3.example.com:1080

# Proxy pool settings
PROXY_ROTATION_STRATEGY=health_based  # Options: health_based, round_robin, random
PROXY_CIRCUIT_BREAKER_THRESHOLD=5     # Consecutive failures before opening circuit
PROXY_CIRCUIT_BREAKER_TIMEOUT=300     # Seconds before retrying failed proxy
PROXY_MAX_RETRIES=3                   # Maximum retries per request
PROXY_INITIAL_BACKOFF=1.0             # Initial backoff delay (seconds)
PROXY_MAX_BACKOFF=60.0                # Maximum backoff delay (seconds)
```

### Rotation Strategies

1. **health_based** (default): Selects proxy with highest health score
2. **round_robin**: Rotates through proxies in order
3. **random**: Randomly selects from available proxies

## Usage Examples

### Basic Usage

The proxy pool is automatically initialized and used when proxies are configured:

```python
# Set environment variables
export PROXY_SERVERS="http://proxy1:8080,http://proxy2:8080,http://proxy3:8080"

# Run scraper - proxy pool is used automatically
python main.py --run-once
```

### Programmatic Usage

```python
from proxy_pool import ProxyPool

# Initialize pool
proxies = [
    {'server': 'http://proxy1.example.com:8080'},
    {'server': 'http://proxy2.example.com:8080', 'username': 'user', 'password': 'pass'},
    {'server': 'socks5://proxy3.example.com:1080'}
]

pool = ProxyPool(
    proxies=proxies,
    rotation_strategy='health_based',
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=300
)

# Get next proxy
proxy = pool.get_next_proxy()

# Execute operation with retry
def my_operation(proxy=None):
    # Your operation here
    # proxy dict contains 'server', optionally 'username', 'password'
    return result

result = pool.execute_with_retry(
    my_operation,
    operation_name="my_operation"
)

# Mark success/failure manually
pool.mark_success(proxy, latency=1.5)
pool.mark_failure(proxy, error_type="timeout")
```

### With Playwright

```python
from playwright.sync_api import sync_playwright
from proxy_pool import ProxyPool

pool = ProxyPool(proxies=[...])

with sync_playwright() as p:
    # Get proxy from pool
    proxy = pool.get_next_proxy()
    
    browser = p.chromium.launch(
        proxy={
            'server': proxy['server'],
            'username': proxy.get('username'),
            'password': proxy.get('password')
        }
    )
    
    try:
        page = browser.new_page()
        page.goto("https://www.instagram.com/explore/")
        # ... scraping ...
        pool.mark_success(proxy)
    except Exception as e:
        pool.mark_failure(proxy, error_type=type(e).__name__)
        raise
```

## Health Scoring

### How Health Scores Work

- **Initial Score**: 100.0 (perfect health)
- **Success**: +2.0 points
- **Failure**: -5.0 points (default), -3.0 for timeouts, -10.0 for auth failures
- **Range**: 0.0 to 100.0

### Health States

- **HEALTHY** (70-100): Proxy is working well
- **DEGRADED** (40-69): Proxy has some issues but still usable
- **UNHEALTHY** (0-39): Proxy is having problems
- **CIRCUIT_OPEN**: Circuit breaker is open, proxy temporarily disabled

## Circuit Breaker

### How It Works

1. **Threshold**: After N consecutive failures (default: 5), circuit opens
2. **Timeout**: Circuit stays open for T seconds (default: 300)
3. **Recovery**: After timeout, circuit closes and proxy can be tried again
4. **Success**: If operation succeeds, circuit closes immediately

### Configuration

```python
pool = ProxyPool(
    proxies=proxies,
    circuit_breaker_threshold=5,    # Open after 5 failures
    circuit_breaker_timeout=300      # Stay open for 5 minutes
)
```

## Retry with Exponential Backoff

### How It Works

1. **First attempt**: Immediate
2. **Second attempt**: Wait `initial_backoff` seconds (default: 1.0s)
3. **Third attempt**: Wait `initial_backoff * multiplier` seconds (default: 2.0s)
4. **Fourth attempt**: Wait `initial_backoff * multiplier^2` seconds (default: 4.0s)
5. **Maximum**: Never exceed `max_backoff` seconds (default: 60.0s)

### Example

```
Attempt 1: Immediate
Attempt 2: Wait 1.0s
Attempt 3: Wait 2.0s
Attempt 4: Wait 4.0s
Attempt 5: Wait 8.0s
...
Maximum: 60.0s
```

## Monitoring

### Get Health Summary

```python
pool = initialize_proxy_pool()
if pool:
    health = pool.get_health_summary()
    print(health)
    # {
    #     'total_proxies': 3,
    #     'healthy': 2,
    #     'degraded': 1,
    #     'unhealthy': 0,
    #     'circuit_open': 0,
    #     'total_requests': 150,
    #     'total_successful': 145,
    #     'total_failed': 5,
    #     'overall_success_rate': 96.67,
    #     'available_proxies': 2
    # }
```

### Get Detailed Stats

```python
stats = pool.get_proxy_stats()
for proxy_key, stat in stats.items():
    print(f"{proxy_key}:")
    print(f"  Health Score: {stat['health_score']}")
    print(f"  Success Rate: {stat['success_rate']}%")
    print(f"  State: {stat['health_state']}")
    print(f"  Circuit Open: {stat['circuit_breaker_open']}")
```

### Health Checks

```python
# Perform health check on all proxies
results = pool.health_check(
    test_url="https://www.google.com",
    timeout=5
)
# Returns: {'proxy1': True, 'proxy2': False, ...}
```

## Integration with Existing Code

The proxy pool is automatically integrated into:

1. **Browser Context Creation**: Proxy selected from pool
2. **Navigation Operations**: Automatic retry with proxy rotation
3. **Error Handling**: Automatic proxy failure tracking
4. **Metrics**: Proxy health included in metrics summary

## Best Practices

1. **Use Multiple Proxies**: More proxies = better resilience
2. **Monitor Health**: Regularly check proxy health summary
3. **Adjust Thresholds**: Tune circuit breaker based on your needs
4. **Health Checks**: Enable periodic health checks for proactive monitoring
5. **Logging**: Monitor proxy pool logs for issues

## Troubleshooting

### No Healthy Proxies Available

**Symptom**: `No healthy proxies available`

**Solutions**:
- Check proxy connectivity
- Reset circuit breakers: `pool._reset_circuit_breakers()`
- Lower circuit breaker threshold
- Add more proxies

### All Proxies Failing

**Symptom**: All proxies marked as failed

**Solutions**:
- Verify proxy credentials
- Check network connectivity
- Test proxies manually
- Review error logs for patterns

### High Latency

**Symptom**: Slow operations

**Solutions**:
- Check proxy server performance
- Use proxies closer to target servers
- Monitor average latency in stats
- Consider removing slow proxies

## Example Configuration

```bash
# .env file
PROXY_SERVERS=http://proxy1.example.com:8080,http://proxy2.example.com:8080,http://proxy3.example.com:8080
PROXY_ROTATION_STRATEGY=health_based
PROXY_CIRCUIT_BREAKER_THRESHOLD=5
PROXY_CIRCUIT_BREAKER_TIMEOUT=300
PROXY_MAX_RETRIES=3
PROXY_INITIAL_BACKOFF=1.0
PROXY_MAX_BACKOFF=60.0
```

## Advanced Usage

### Custom Rotation Strategy

```python
class CustomProxyPool(ProxyPool):
    def _custom_select(self, proxies):
        # Your custom selection logic
        return selected_proxy
```

### Manual Proxy Management

```python
# Manually mark proxy as failed
pool.mark_failure(proxy, error_type="custom_error")

# Manually mark proxy as successful
pool.mark_success(proxy, latency=1.5)

# Reset circuit breakers
pool._reset_circuit_breakers()
```

## Metrics Integration

Proxy pool metrics are automatically included in observability:

- Proxy health scores
- Success/failure rates
- Circuit breaker states
- Latency statistics

All metrics are logged at the end of each scraper job run.

