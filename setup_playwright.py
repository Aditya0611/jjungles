"""
Setup script to install Playwright browsers
Run this once after installing requirements.txt
"""

import subprocess
import sys

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("Installing Playwright browsers...")
    print("This may take a few minutes...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✅ Playwright browsers installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Playwright browsers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_playwright_browsers()

