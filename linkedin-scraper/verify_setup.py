from linkedin_hashtag_scraper_playwright import LinkedInHashtagScraper, ProxyRotator
from logger import logger
import os
import json

def verify_components():
    print("Checking components...")
    
    # Check Logger
    logger.info("Test log message")
    if os.path.exists("scraper_logs.jsonl"):
        print("✅ Logger created log file")
    else:
        print("❌ Logger failed to create log file")

    # Check ProxyRotator
    try:
        rotator = ProxyRotator("proxies.txt")
        print(f"✅ ProxyRotator initialized (Failed proxies: {len(rotator.failed_proxies)})")
    except Exception as e:
        print(f"❌ ProxyRotator init failed: {e}")

    # Check Scraper Init
    try:
        scraper = LinkedInHashtagScraper(headless=True, use_proxies=False, use_supabase=False)
        print("✅ LinkedInHashtagScraper initialized")
        
        # Check save_dashboard_data existence
        if hasattr(scraper, 'save_dashboard_data'):
            print("✅ save_dashboard_data method exists")
        else:
            print("❌ save_dashboard_data method missing")
            
    except Exception as e:
        print(f"❌ Scraper init failed: {e}")

if __name__ == "__main__":
    verify_components()
