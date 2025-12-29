# Proxy Configuration for Instagram Scraper

## Overview

The scraper now supports proxy configuration to help with:
- **Avoiding rate limiting** - Rotate IPs to prevent blocks
- **Bypassing IP-based blocks** - Use different IPs if your main IP is blocked
- **Geographic restrictions** - Access region-specific content
- **Better anonymity** - Hide your real IP address

## Configuration

### Environment Variables

Set these environment variables to enable proxy support:

```bash
# Proxy server (required if using proxy)
PROXY_SERVER="http://proxy.example.com:8080"

# Or for SOCKS5 proxy:
PROXY_SERVER="socks5://proxy.example.com:1080"

# Optional: Proxy authentication
PROXY_USERNAME="your_proxy_username"
PROXY_PASSWORD="your_proxy_password"

# Optional: Hosts to bypass proxy (comma-separated)
PROXY_BYPASS="localhost,127.0.0.1,*.local"
```

### Proxy Server Formats

The scraper supports multiple proxy protocols:

1. **HTTP Proxy**:
   ```bash
   PROXY_SERVER="http://proxy.example.com:8080"
   ```

2. **HTTPS Proxy**:
   ```bash
   PROXY_SERVER="https://proxy.example.com:8080"
   ```

3. **SOCKS5 Proxy**:
   ```bash
   PROXY_SERVER="socks5://proxy.example.com:1080"
   ```

4. **SOCKS4 Proxy**:
   ```bash
   PROXY_SERVER="socks4://proxy.example.com:1080"
   ```

5. **Proxy with Authentication in URL**:
   ```bash
   PROXY_SERVER="http://username:password@proxy.example.com:8080"
   ```

## Usage Examples

### Basic HTTP Proxy

```bash
export PROXY_SERVER="http://proxy.example.com:8080"
python main.py --run-once
```

### SOCKS5 Proxy with Authentication

```bash
export PROXY_SERVER="socks5://proxy.example.com:1080"
export PROXY_USERNAME="myuser"
export PROXY_PASSWORD="mypass"
python main.py --run-once
```

### Proxy with Bypass List

```bash
export PROXY_SERVER="http://proxy.example.com:8080"
export PROXY_BYPASS="localhost,127.0.0.1,*.local,supabase.co"
python main.py --run-once
```

## GitHub Actions Configuration

To use proxy in GitHub Actions, add it to your workflow secrets:

1. Go to your repository → Settings → Secrets and variables → Actions
2. Add a new secret:
   - Name: `PROXY_SERVER`
   - Value: `http://your-proxy-server:port`

3. Update `.github/workflows/instagram_scraper.yml`:

```yaml
- name: Run Instagram Scraper
  run: python main.py --run-once
  env:
    INSTAGRAM_USERNAME: ${{ secrets.INSTAGRAM_USERNAME }}
    INSTAGRAM_PASSWORD: ${{ secrets.INSTAGRAM_PASSWORD }}
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
    HEADLESS: "true"
    PROXY_SERVER: ${{ secrets.PROXY_SERVER }}  # Add this
    PROXY_USERNAME: ${{ secrets.PROXY_USERNAME }}  # Optional
    PROXY_PASSWORD: ${{ secrets.PROXY_PASSWORD }}  # Optional
```

## Proxy Rotation (Advanced)

For proxy rotation, you can:

1. **Use a proxy rotation service** that provides a single endpoint
2. **Create a wrapper script** that rotates proxies between runs
3. **Use environment variables** and change them before each run

Example rotation script:

```python
# rotate_proxy.py
import os
import random

proxies = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]

selected_proxy = random.choice(proxies)
os.environ["PROXY_SERVER"] = selected_proxy
print(f"Using proxy: {selected_proxy}")

# Then run main.py
```

## Testing Proxy Connection

To test if your proxy is working:

```bash
# Set proxy
export PROXY_SERVER="http://your-proxy:8080"

# Run scraper
python main.py --run-once

# Check logs for proxy confirmation
# You should see: "🔒 Using proxy: your-proxy:8080"
```

## Troubleshooting

### Proxy Connection Failed

If you see connection errors:
1. **Verify proxy server** is accessible
2. **Check credentials** if using authentication
3. **Test proxy** with curl or browser first
4. **Check firewall** rules

### Proxy Not Working

If proxy is set but not being used:
1. **Check environment variable** is set correctly
2. **Verify format** matches expected pattern
3. **Check logs** for proxy initialization message
4. **Ensure proxy supports** the protocol you're using

### Rate Limiting Still Happening

Even with proxy:
1. **Use residential proxies** instead of datacenter proxies
2. **Rotate proxies** more frequently
3. **Reduce request frequency** (increase delays)
4. **Use multiple accounts** with different proxies

## Best Practices

1. **Use Residential Proxies**: Better success rate than datacenter proxies
2. **Rotate Proxies**: Don't use the same proxy for all requests
3. **Test Proxies First**: Verify proxy works before using in production
4. **Monitor Proxy Health**: Check proxy uptime and response times
5. **Use Proxy Pools**: Have multiple proxies ready for rotation

## Security Notes

⚠️ **Important**:
- Never commit proxy credentials to git
- Use environment variables or secrets management
- Rotate proxy credentials regularly
- Use HTTPS/SOCKS5 for encrypted connections when possible

## Supported Proxy Providers

The scraper works with any proxy that supports:
- HTTP/HTTPS proxies
- SOCKS4/SOCKS5 proxies
- Basic authentication
- Standard proxy protocols

Popular proxy providers:
- Bright Data (formerly Luminati)
- Smartproxy
- Oxylabs
- ProxyMesh
- Private proxies

## Disabling Proxy

To disable proxy, simply don't set the `PROXY_SERVER` environment variable, or set it to empty:

```bash
unset PROXY_SERVER
# or
export PROXY_SERVER=""
```

