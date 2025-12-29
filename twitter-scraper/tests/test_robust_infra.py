
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from twitter_scraper_app.db import TrendRecord, process_retry_queue
from twitter_scraper_app.services import insert_fresh_data_only
from twitter_scraper_app.queue_manager import retry_queue
import twitter_scraper_app.config as config

async def test_retry_queue():
    print("\n--- Testing Retry Queue ---")
    # 1. Clear queue
    retry_queue.clear()
    print(f"Queue cleared. Count: {retry_queue.count()}")

    # 2. Simulate failure by providing invalid Supabase client or setting a flag
    # We can just temporarily break the supabase reference or use a mock
    from twitter_scraper_app import db
    original_supabase = db.supabase
    db.supabase = None # Force failure in insert_fresh_data_only
    
    # 3. Try to insert data
    topics = [{
        "topic": "#TestHashtagQueue",
        "count": "100K",
        "engagement_score": 5.0,
        "sentiment": "Positive",
        "sentiment_polarity": 0.5,
        "language": "en",
        "post_content": "This is a test tweet for queueing."
    }]
    
    print("Attempting to insert topics with 'broken' Supabase connection...")
    await insert_fresh_data_only(topics)
    
    # 4. Verify count in queue
    count = retry_queue.count()
    print(f"Items in local queue: {count}")
    if count == 1:
        print("✅ SUCCESS: Record was correctly cached locally.")
    else:
        print("❌ FAILURE: Record was NOT cached.")

    # 5. Restore connection and process queue
    db.supabase = original_supabase
    print("Restored Supabase connection. Processing queue...")
    await process_retry_queue()
    
    final_count = retry_queue.count()
    print(f"Remaining items in queue: {final_count}")
    if final_count == 0:
        print("✅ SUCCESS: Queue was processed and cleared.")
    else:
        print("❌ FAILURE: Queue still has items.")

async def test_proxy_enforcement():
    print("\n--- Testing Proxy Enforcement ---")
    # Backup original state
    original_require = config.proxy_manager.require_proxy
    original_proxies = config.proxy_manager.proxies
    
    # Save env vars
    env_keys = ["PROXY_LIST", "HTTP_PROXY", "HTTPS_PROXY", "REQUIRE_PROXY", "PROXY"]
    env_backup = {k: os.environ.get(k) for k in env_keys}
    
    try:
        # 1. Clear everything
        for k in env_keys:
            if k in os.environ: del os.environ[k]
        
        config.proxy_manager.proxies = []
        config.proxy_manager.require_proxy = True
        
        print("Test 1: Calling get_proxy() with empty list...")
        try:
            config.proxy_manager.get_proxy()
            print("❌ FAILURE: get_proxy() did not raise RuntimeError for empty list.")
        except RuntimeError as e:
            print(f"✅ SUCCESS: get_proxy() raised expected error: {e}")

        print("Test 2: Calling _load_proxies() with no env vars...")
        try:
            config.proxy_manager._load_proxies()
            print("❌ FAILURE: _load_proxies() did not raise RuntimeError for missing proxies.")
        except RuntimeError as e:
            print(f"✅ SUCCESS: _load_proxies() raised expected error: {e}")
            
    finally:
        # Restore
        config.proxy_manager.require_proxy = original_require
        config.proxy_manager.proxies = original_proxies
        for k, v in env_backup.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

async def main():
    await test_retry_queue()
    await test_proxy_enforcement()

if __name__ == "__main__":
    asyncio.run(main())
