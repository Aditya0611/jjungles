# Proxy Configuration Guide

## Overview

The scraper now supports proxy rotation to bypass IP-based rate limiting and connection timeouts from TikTok.

## Quick Setup

### Option 1: Free Proxy (Not Recommended for Production)

```powershell
# Windows PowerShell
$env:PROXY_SERVER="http://proxy-server.com:8080"

# Test the scraper
python base.py
```

### Option 2: Authenticated Proxy (Recommended)

```powershell
# Windows PowerShell
$env:PROXY_SERVER="http://proxy-server.com:8080"
$env:PROXY_USERNAME="your_username"
$env:PROXY_PASSWORD="your_password"

# Test the scraper
python base.py
```

### Option 3: Premium Proxy Services

**Recommended providers:**
- **Bright Data** (formerly Luminati) - https://brightdata.com/
- **Smartproxy** - https://smartproxy.com/
- **Oxylabs** - https://oxylabs.io/
- **ScraperAPI** - https://scraperapi.com/

Example with Bright Data:
```powershell
$env:PROXY_SERVER="http://brd.superproxy.io:22225"
$env:PROXY_USERNAME="brd-customer-YOUR_ID-zone-residential"
$env:PROXY_PASSWORD="your_password"
```

## Free Proxy Lists (Testing Only)

⚠️ **Warning**: Free proxies are unreliable, slow, and may be malicious. Use only for testing.

```powershell
# Example free proxies (may not work)
$env:PROXY_SERVER="http://47.88.62.42:80"
# or
$env:PROXY_SERVER="http://proxy.free-proxy.net:8080"
```

Free proxy sources:
- https://www.free-proxy-list.net/
- https://hidemy.name/en/proxy-list/
- https://spys.one/en/

## Verifying Proxy Connection

Test if your proxy is working:

```powershell
# Create a test file: test_proxy.py
python -c "import os; from playwright.async_api import async_playwright; import asyncio; async def test(): async with async_playwright() as p: browser = await p.chromium.launch(); context = await browser.new_context(proxy={'server': os.environ.get('PROXY_SERVER')}); page = await context.new_page(); await page.goto('https://api.ipify.org?format=json'); print(await page.content()); await browser.close(); asyncio.run(test())"
```

## Alternative Solutions (No Proxy Required)

### 1. Use Your Mobile Hotspot

```powershell
# Connect to mobile hotspot and run
python base.py
```

### 2. Wait and Retry Later

TikTok may temporarily block your IP. Try again in:
- 15-30 minutes for soft blocks
- 1-2 hours for moderate blocks
- 24 hours for hard blocks

### 3. Use VPN

```powershell
# Connect to VPN first, then run
python base.py
```

Popular VPN services:
- NordVPN
- ExpressVPN
- ProtonVPN (Free tier available)
- Windscribe (Free tier available)

### 4. Run from Different Network

Try running from:
- Different Wi-Fi network
- Office/work network
- Public Wi-Fi (use with caution)
- Cloud VM (AWS, GCP, Azure)

## Cloud-Based Solution

Deploy to cloud to avoid IP blocks:

### AWS EC2
```bash
# Launch EC2 instance
aws ec2 run-instances --image-id ami-0c55b159cbfafe1f0 --instance-type t2.micro

# SSH into instance
ssh -i key.pem ubuntu@ec2-instance

# Install and run
git clone <repo>
cd tik-tok-ampify
pip install -r requirements.txt
playwright install chromium --with-deps
python base.py
```

### GitHub Actions (Already Configured)

Your scraper already has GitHub Actions CI/CD that runs on GitHub's infrastructure:

```bash
# Trigger manual run
gh workflow run scrape-tiktok.yml
```

This avoids your IP entirely!

## Troubleshooting

### Error: "Proxy connection failed"

1. Verify proxy is online:
```powershell
curl --proxy $env:PROXY_SERVER https://api.ipify.org
```

2. Check authentication:
```powershell
# Ensure username/password are correct
echo $env:PROXY_USERNAME
echo $env:PROXY_PASSWORD
```

### Error: "Connection still timing out with proxy"

1. Try different proxy server
2. Increase timeout in code (already set to 90s)
3. Use residential proxy instead of datacenter proxy
4. Contact proxy provider support

### Error: "Too slow with proxy"

Premium proxies are faster than free ones. Consider:
- Upgrading to paid proxy service
- Using residential proxies
- Selecting geographically closer proxy servers

## Cost Comparison

| Solution | Cost | Reliability | Setup Time |
|----------|------|-------------|------------|
| Free Proxy | $0 | ⭐ Poor | 5 min |
| VPN Service | $5-12/mo | ⭐⭐⭐ Good | 10 min |
| Mobile Hotspot | Data charges | ⭐⭐⭐ Good | 2 min |
| Premium Proxy | $50-500/mo | ⭐⭐⭐⭐⭐ Excellent | 15 min |
| GitHub Actions | $0 (included) | ⭐⭐⭐⭐ Very Good | 0 min (already setup) |
| Cloud VM | $5-20/mo | ⭐⭐⭐⭐ Very Good | 30 min |

## Recommended Approach

**For immediate testing:**
1. Try running without proxy first (wait 1-2 hours if blocked)
2. Use GitHub Actions (already configured)
3. Switch to mobile hotspot

**For production:**
1. Use GitHub Actions scheduled runs (free, reliable)
2. Deploy to cloud VM with rotating IPs
3. Use premium proxy service if high volume needed

## Configuration in Code

The scraper automatically:
- Uses direct connection on first attempt
- Switches to proxy on retry attempts (if configured)
- Rotates between alternate URLs
- Applies exponential backoff

No code changes needed - just set environment variables!

## Support

If still experiencing issues:
1. Check `debug_*.html` files for error details
2. Review logs for specific error messages
3. Try the GitHub Actions workflow (no proxy needed)
4. Consider running during off-peak hours (late night US time)
