import asyncio
import sys
from twitter_scraper_app.utils import logger
from twitter_scraper_app.config import SCRAPE_VERSION_ID
from twitter_scraper_app.db import log_scrape_start, log_scrape_end
from twitter_scraper_app.services import (
    get_trending_topics,
    process_single_topic,
    insert_fresh_data_only
)

async def main():
    """
    Main orchestration function for the Twitter Trending scraper.
    
    Workflow:
    1. Log start of run.
    2. Process any pending local retry queue items.
    3. Scrape trending topics concurrently from multiple mirrors.
    4. Enrich topics with sentiment, engagement, and language data (concurrently).
    5. Sync all fresh data to Supabase.
    6. Log completion and exit.
    """
    run_id = log_scrape_start("twitter_scraper")
    
    # Process local queue at start to ensure database consistency
    from twitter_scraper_app.db import process_retry_queue
    await process_retry_queue()
    
    logger.info("twitter_scrape_start", extra={"event": "twitter_scrape_start", "data": {"version_id": SCRAPE_VERSION_ID}})
    
    try:
        # 1. Fetch trending hashtags
        trending_topics = await get_trending_topics()
        
        if not trending_topics:
            logger.warning("No trending topics found.")
            log_scrape_end(run_id, "failed", 0, "No trending topics found")
            return

        logger.info(f"Found {len(trending_topics)} trends. Starting concurrent enrichment...")
        
        # 2. Enrich topics concurrently with limited parallelism
        sem = asyncio.Semaphore(5)
        
        async def bounded_process(t):
            async with sem:
                try:
                    return await process_single_topic(t)
                except Exception as e:
                    logger.error(f"Error processing topic {t.get('topic')}: {e}")
                    return None
        
        tasks = [bounded_process(topic) for topic in trending_topics]
        processed_topics = await asyncio.gather(*tasks)
        
        # Filter out failed encrichments
        processed_topics = [p for p in processed_topics if p]
        
        # 3. Insert and sync
        result = await insert_fresh_data_only(processed_topics)
        
        inserted, updated = result if result else (0, 0)
        log_scrape_end(run_id, "success", inserted + updated)
            
    except Exception as e:
        logger.error(f"Fatal error in scraper orchestration: {e}")
        log_scrape_end(run_id, "failed", 0, str(e))
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraper execution interrupted by user.")
    except Exception as e:
        logger.error(f"Critical unhandled exception: {e}")
        sys.exit(1)
