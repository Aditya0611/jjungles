import os
import sys
import time
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from playwright.sync_api import sync_playwright

# Local modules
from models import Config, PLATFORM_NAME, VERSION_ID
from auth import login_instagram, verify_logged_in
from discovery import discover_hashtags
from engagement import analyze_hashtag_engagement
from db import save_trends_to_database
from observability import setup_structured_logging, metrics
from scraper_run_logger import ScraperRunLogger
from supabase import create_client, Client
from proxy_pool import ProxyPool, parse_proxy_string
from proxy_wrappers import login_with_retry, create_browser_context_with_retry

# Initialize logging
LOG_FILE_NAME = "instagram_scraper.log"
LOG_DIR = Path(__file__).parent
LOG_FILE_PATH = LOG_DIR / LOG_FILE_NAME

logger = setup_structured_logging(str(LOG_FILE_PATH))
run_logger: Optional[ScraperRunLogger] = None

def run_scraper_job(supabase: Client, run_once: bool = False):
    """Main orchestration job for the scraper."""
    import models
    models.VERSION_ID = str(uuid.uuid4())
    global run_logger
    run_logger = ScraperRunLogger(supabase, models.VERSION_ID)
    run_logger.start_run()
    logger.info(f"Starting scraper run {models.VERSION_ID}")
    
    # 1. Load Proxies (STRICT ENFORCEMENT)
    proxy_list = []
    proxy_file = Path(Config.PROXY_LIST_PATH)
    if proxy_file.exists():
        try:
            with open(proxy_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parsed = parse_proxy_string(line)
                        if parsed:
                            proxy_list.append(parsed)
            logger.info(f"Loaded {len(proxy_list)} proxies from {Config.PROXY_LIST_PATH}")
        except Exception as e:
            logger.error(f"Error reading proxy file: {e}")
            run_logger.complete_run_failure(f"Error reading proxy file: {e}")
            return
    
    if Config.REQUIRE_PROXIES and not proxy_list:
        error_msg = f"CRITICAL: Proxies required (REQUIRE_PROXIES=True) but no valid proxies found in {Config.PROXY_LIST_PATH}"
        logger.error(error_msg)
        run_logger.complete_run_failure(error_msg, "ProxyConfigError")
        return
        
    proxy_pool = ProxyPool(proxy_list) if proxy_list else None
    
    with sync_playwright() as p:
        # Browser setup
        browser = p.chromium.launch(headless=Config.HEADLESS)
        context = None
        page = None
        
        try:
            # 2. Login with Retry & Proxy Rotation
            # This handles context creation, proxy assignment, and login retries
            context, page, login_success = login_with_retry(browser, proxy_pool)
            
            if not login_success or not page:
                error_msg = "Failed to login to Instagram after retries"
                logger.error(error_msg)
                run_logger.complete_run_failure(error_msg, "LoginError")
                return
            
            # 3. Discovery
            trending_hashtags = discover_hashtags(page)
            if not trending_hashtags:
                logger.warning("No hashtags discovered")
                run_logger.complete_run_failure("No hashtags discovered", "DiscoveryError")
                return
            
            run_logger.log_step("discovery", f"Discovered {len(trending_hashtags)} hashtags", metadata={'count': len(trending_hashtags)})
                
            # 4. Engagement Analysis
            trend_records = []
            for hashtag_info in trending_hashtags:
                engagement_data = analyze_hashtag_engagement(page, hashtag_info)
                if engagement_data:
                    from models import TrendRecord
                    record = TrendRecord.from_instagram_data(hashtag_info, engagement_data, models.VERSION_ID)
                    trend_records.append(record)
            
            # 5. Save to DB (Unified Path)
            saved_count = 0
            new_records = 0 # db.py doesn't return this breakdown yet, assuming same for now
            if trend_records:
                results = save_trends_to_database(supabase, trend_records)
                saved_count = results.get("success", 0)
                logger.info(f"Run completed successfully. Saved {saved_count} trends.")
                
            run_logger.complete_run_success(
                hashtags_discovered=len(trending_hashtags),
                hashtags_saved=saved_count,
                new_records=new_records, # Placeholder until db returns details
                updated_records=0,
                proxy_used=page.context.options.get('proxy', {}).get('server', 'None'),
                proxy_pool_size=len(proxy_list)
            )
            
        except Exception as e:
            logger.exception(f"Critical error during scraper run: {e}")
            run_logger.complete_run_failure(str(e), type(e).__name__)
        finally:
            if context: context.close()
            browser.close()

if __name__ == "__main__":
    # Validate config
    if not Config.validate():
        sys.exit(1)
        
    # Initialize Supabase
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    # run_logger will be initialized inside run_scraper_job
    
    # Simple CLI argument handling
    if "--run-once" in sys.argv:
        run_scraper_job(supabase, run_once=True)
    else:
        # Scheduler logic here
        pass