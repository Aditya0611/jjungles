# Client Delivery Package Instructions

## 📦 Package Contents

The client delivery package (`instagram_client_delivery_YYYYMMDD_HHMMSS.zip`) contains:

### Essential Files:
- ✅ **main.py** - Main Instagram scraper (credentials sanitized)
- ✅ **requirements.txt** - Python dependencies
- ✅ **README.md** - Project documentation
- ✅ **.gitignore** - Git ignore rules
- ✅ **.github/** - GitHub Actions workflow files (if applicable)

## 🔒 Security Features

All sensitive credentials have been sanitized and replaced with placeholders:
- Instagram username → `YOUR_INSTAGRAM_USERNAME`
- Instagram password → `YOUR_INSTAGRAM_PASSWORD`
- Supabase URL → `YOUR_SUPABASE_URL`
- Supabase Key → `YOUR_SUPABASE_KEY`

## 🚀 Setup Instructions for Client

### 1. Extract the Package
```bash
unzip instagram_client_delivery_YYYYMMDD_HHMMSS.zip
cd instagram
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Credentials

**Environment Variables (Recommended)**
Create a `.env` file with these keys:
- `INSTAGRAM_USERNAME`
- `INSTAGRAM_PASSWORD`
- `SUPABASE_URL`
- `SUPABASE_KEY`

**Proxy Settings:**
- `REQUIRE_PROXIES=true`: Strictly enforce proxy usage (fails if no proxy available).
- `REQUIRE_PROXIES=false`: Allow running without proxies (fallback mode).
- `PROXY_SERVER`, `PROXY_USERNAME`, `PROXY_PASSWORD`: Your proxy credentials.

### 4. Install Playwright Browsers
```bash
playwright install chromium
```

### 5. Run the Scraper
```bash
# Run once (test mode)
python main.py --run-once

# Run continuously (scheduled)
python main.py
```

## 📋 What Was Excluded

The following files were **NOT** included in the delivery package:
- ❌ Debug screenshots (*.png)
- ❌ Log files (*.log)
- ❌ Export files (*.json, *.csv)
- ❌ Backup files (main copy.py)
- ❌ Test/utility scripts
- ❌ Internal documentation files
- ❌ Virtual environment (vrnv/)
- ❌ Cache directories (__pycache__/)

## ✅ Quality Assurance

Before delivery, the package was:
- ✅ Credentials sanitized
- ✅ Unimportant files removed
- ✅ Only essential files included
- ✅ Tested for completeness
- ✅ Ready for production use

## 📞 Support

If the client needs assistance with setup or configuration, refer them to the README.md file or contact the development team.

