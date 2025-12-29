# How to Set Proxy Server Configuration

## Option 1: Environment Variables (Local Development)

### Windows PowerShell

**Temporary (Current Session Only):**
```powershell
$env:PROXY_SERVER = "http://proxy.example.com:8080"
$env:PROXY_USERNAME = "your_username"  # Optional
$env:PROXY_PASSWORD = "your_password"  # Optional
$env:PROXY_BYPASS = "localhost,127.0.0.1"  # Optional

# Then run scraper
python main.py --run-once
```

**Permanent (User Profile):**
```powershell
# Set permanently for your user
[System.Environment]::SetEnvironmentVariable("PROXY_SERVER", "http://proxy.example.com:8080", "User")
[System.Environment]::SetEnvironmentVariable("PROXY_USERNAME", "your_username", "User")
[System.Environment]::SetEnvironmentVariable("PROXY_PASSWORD", "your_password", "User")

# Restart terminal or run:
refreshenv
```

### Windows Command Prompt (CMD)

```cmd
set PROXY_SERVER=http://proxy.example.com:8080
set PROXY_USERNAME=your_username
set PROXY_PASSWORD=your_password
python main.py --run-once
```

### Linux/Mac (Bash)

**Temporary:**
```bash
export PROXY_SERVER="http://proxy.example.com:8080"
export PROXY_USERNAME="your_username"
export PROXY_PASSWORD="your_password"
python main.py --run-once
```

**Permanent (Add to ~/.bashrc or ~/.zshrc):**
```bash
echo 'export PROXY_SERVER="http://proxy.example.com:8080"' >> ~/.bashrc
echo 'export PROXY_USERNAME="your_username"' >> ~/.bashrc
echo 'export PROXY_PASSWORD="your_password"' >> ~/.bashrc
source ~/.bashrc
```

## Option 2: Create a .env File (Recommended for Local)

1. **Create a `.env` file** in your project root (`E:\instagram\.env`):

```env
PROXY_SERVER=http://proxy.example.com:8080
PROXY_USERNAME=your_username
PROXY_PASSWORD=your_password
PROXY_BYPASS=localhost,127.0.0.1
```

2. **Install python-dotenv** (if not already installed):
```bash
pip install python-dotenv
```

3. **Update main.py** to load .env file (add at the top):
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

**Note:** Add `.env` to `.gitignore` to keep credentials safe!

## Option 3: GitHub Actions (CI/CD)

### Step 1: Add Secrets to GitHub

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:
   - `PROXY_SERVER` = `http://proxy.example.com:8080`
   - `PROXY_USERNAME` = `your_username` (optional)
   - `PROXY_PASSWORD` = `your_password` (optional)

### Step 2: Update Workflow File

Edit `.github/workflows/instagram_scraper.yml`:

```yaml
- name: Run Instagram Scraper
  run: python main.py --run-once
  env:
    INSTAGRAM_USERNAME: ${{ secrets.INSTAGRAM_USERNAME }}
    INSTAGRAM_PASSWORD: ${{ secrets.INSTAGRAM_PASSWORD }}
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
    HEADLESS: "true"
    PROXY_SERVER: ${{ secrets.PROXY_SERVER }}  # Add this line
    PROXY_USERNAME: ${{ secrets.PROXY_USERNAME }}  # Optional
    PROXY_PASSWORD: ${{ secrets.PROXY_PASSWORD }}  # Optional
```

## Option 4: Direct in Code (Not Recommended)

⚠️ **Warning:** Only for testing. Never commit credentials to git!

You can temporarily modify `main.py` in the `Config` class:

```python
# In Config class (around line 174)
PROXY_SERVER: Optional[str] = "http://proxy.example.com:8080"  # Temporary
PROXY_USERNAME: Optional[str] = "your_username"
PROXY_PASSWORD: Optional[str] = "your_password"
```

**Remember to remove before committing!**

## Quick Start Guide

### For Local Testing (Easiest)

1. **Open PowerShell in your project directory:**
   ```powershell
   cd E:\instagram
   ```

2. **Set proxy (replace with your actual proxy):**
   ```powershell
   $env:PROXY_SERVER = "http://your-proxy-server.com:8080"
   ```

3. **If proxy requires authentication:**
   ```powershell
   $env:PROXY_USERNAME = "your_username"
   $env:PROXY_PASSWORD = "your_password"
   ```

4. **Run scraper:**
   ```powershell
   python main.py --run-once
   ```

5. **Verify proxy is being used:**
   - Look for: `🔒 Using proxy: your-proxy-server.com:8080` in the output

## Proxy Server Formats

### HTTP Proxy
```
http://proxy.example.com:8080
```

### HTTPS Proxy
```
https://proxy.example.com:8080
```

### SOCKS5 Proxy
```
socks5://proxy.example.com:1080
```

### With Authentication in URL
```
http://username:password@proxy.example.com:8080
```

## Testing Your Proxy

1. **Set the proxy:**
   ```powershell
   $env:PROXY_SERVER = "http://your-proxy:8080"
   ```

2. **Run scraper:**
   ```powershell
   python main.py --run-once
   ```

3. **Check output:**
   - Should see: `🔒 Using proxy: your-proxy:8080`
   - If connection fails, check proxy credentials and server

## Troubleshooting

### Proxy Not Working?

1. **Check if proxy is set:**
   ```powershell
   echo $env:PROXY_SERVER
   ```

2. **Verify proxy format:**
   - Must include protocol: `http://` or `socks5://`
   - Must include port: `:8080`

3. **Test proxy connection:**
   ```powershell
   # Test with curl (if installed)
   curl -x http://proxy.example.com:8080 https://www.instagram.com
   ```

4. **Check logs:**
   - Look for proxy-related errors in the output
   - Check if proxy server is accessible

### Proxy Authentication Failed?

1. **Verify credentials:**
   - Check username/password are correct
   - Try including in URL: `http://user:pass@proxy.com:8080`

2. **Check proxy type:**
   - Some proxies only support specific protocols
   - Try HTTP first, then SOCKS5

## Security Best Practices

✅ **DO:**
- Use environment variables
- Use GitHub Secrets for CI/CD
- Use `.env` file (add to `.gitignore`)
- Rotate proxy credentials regularly

❌ **DON'T:**
- Commit proxy credentials to git
- Hardcode credentials in code
- Share proxy credentials publicly
- Use the same proxy for all requests (if possible)

## Example: Complete Setup

```powershell
# 1. Set proxy
$env:PROXY_SERVER = "socks5://proxy.example.com:1080"
$env:PROXY_USERNAME = "myuser"
$env:PROXY_PASSWORD = "mypass"

# 2. Verify it's set
echo "Proxy: $env:PROXY_SERVER"

# 3. Run scraper
python main.py --run-once

# 4. Check output for proxy confirmation
# Should see: 🔒 Using proxy: proxy.example.com:1080
```

## Need Help?

If proxy still doesn't work:
1. Check proxy server is running and accessible
2. Verify credentials are correct
3. Test proxy with a browser or curl first
4. Check firewall/network settings
5. Try a different proxy protocol (HTTP vs SOCKS5)

