"""
Offline Queue Processor Worker & Job Runner
Automatically processes:
1. Queued uploads from local cache to Supabase
2. Retry jobs from JobQueue (e.g. failed scrapes)
"""

import asyncio
import logging
import time
import os
import sys

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QueueWorker")

# Import dependencies
try:
    from cache_manager import LocalCache
    from base import init_supabase, run_scraper, SUPABASE_URL, SUPABASE_KEY
    from job_queue import JobQueue
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import dependencies: {e}")
    DEPENDENCIES_AVAILABLE = False


async def process_offline_queue(max_items: int = 10) -> int:
    """
    Process queued uploads from local cache to Supabase.
    """
    if not DEPENDENCIES_AVAILABLE:
        return 0
    
    try:
        cache = LocalCache()
        supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
        
        if not supabase:
            logger.warning("Supabase not available, cannot process offline queue")
            return 0
        
        queued_items = cache.fetch_offline_queue(limit=max_items)
        if not queued_items:
            return 0
        
        logger.info(f"Processing {len(queued_items)} items from offline queue")
        processed_count = 0
        
        for item in queued_items:
            try:
                table_name = item.get('table_name', 'tiktok')
                data = item.get('data', [])
                item_id = item.get('id')
                
                if not data:
                    cache.remove_offline_item(item_id)
                    continue
                
                # Upload logic (simplified)
                batch_size = 100
                for i in range(0, len(data), batch_size):
                    batch = data[i:i+batch_size]
                    try:
                        # Just insert for offline queue processing
                        supabase.table(table_name).insert(batch).execute()
                    except Exception as batch_error:
                        # If duplicate, we might want to ignore or use upsert
                        if "duplicate key" in str(batch_error):
                            logger.warning(f"Duplicate key error, skipping batch: {batch_error}")
                        else:
                            raise
                
                cache.remove_offline_item(item_id)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process offline item {item.get('id')}: {e}")
        
        return processed_count
        
    except Exception as e:
        logger.error(f"Error in process_offline_queue: {e}")
        return 0


async def process_job_queue(max_jobs: int = 5) -> int:
    """
    Process pending jobs from the persistent JobQueue.
    """
    if not DEPENDENCIES_AVAILABLE:
        return 0
        
    try:
        supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
        if not supabase:
            return 0
            
        job_queue = JobQueue(supabase)
        jobs = job_queue.fetch_pending_jobs(limit=max_jobs)
        
        if not jobs:
            return 0
            
        logger.info(f"Found {len(jobs)} pending jobs in JobQueue")
        processed_count = 0
        
        for job in jobs:
            try:
                if not job_queue.mark_processing(job.id):
                    continue
                
                logger.info(f"Processing job {job.id}: {job.job_type}")
                
                if job.job_type == "scraper":
                    payload = job.payload or {}
                    
                    # Set ENV VAR to prevent recursive job creation
                    os.environ["OS_SCRAPER_WORKER"] = "true"
                    
                    try:
                        # Run the scraper
                        await run_scraper(
                            platform=payload.get("platform", "TikTok"),
                            region=payload.get("region", "en"),
                            headless=payload.get("headless", True),
                            debug=payload.get("debug", False),
                            upload_to_db=payload.get("upload_to_db", True)
                        )
                        job_queue.mark_completed(job.id)
                        logger.info(f"Job {job.id} completed successfully")
                        
                    finally:
                        # Clean up env var
                        if "OS_SCRAPER_WORKER" in os.environ:
                            del os.environ["OS_SCRAPER_WORKER"]
                    
                else:
                    logger.warning(f"Unknown job type: {job.job_type}")
                    job_queue.mark_failed(job.id, "Unknown job type", job.attempts, job.max_attempts)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}")
                job_queue.mark_failed(job.id, str(e), job.attempts, job.max_attempts)
                processed_count += 1
                
        return processed_count
        
    except Exception as e:
        logger.error(f"Error in process_job_queue: {e}")
        return 0


async def run_worker(interval_seconds: int = 60):
    """
    Run the unified worker loop.
    """
    logger.info(f"Starting unified worker (interval: {interval_seconds}s)")
    
    while True:
        try:
            start_time = time.time()
            
            # 1. Process Offline Queue
            offline_processed = await process_offline_queue(max_items=10)
            
            # 2. Process Job Queue
            job_processed = await process_job_queue(max_jobs=5)
            
            duration = time.time() - start_time
            if offline_processed > 0 or job_processed > 0:
                logger.info(f"Cycle complete in {duration:.2f}s: {offline_processed} offline, {job_processed} jobs")
            
            await asyncio.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Offline Queue Worker')
    parser.add_argument('--run-once', action='store_true', help='Run a single processing cycle and exit')
    parser.add_argument('--interval', type=int, default=60, help='Interval between cycles in seconds (default: 60)')
    args = parser.parse_args()

    if args.run_once:
        logger.info("Running single worker cycle...")
        async def run_once():
            try:
                # Process more items in a single run if triggered manually/by cron
                off = await process_offline_queue(max_items=50)
                jobs = await process_job_queue(max_jobs=20)
                logger.info(f"Cycle complete: {off} offline batches processed, {jobs} jobs processed")
                return off, jobs
            except Exception as e:
                logger.error(f"Error in single cycle: {e}")
                return 0, 0
        
        asyncio.run(run_once())
    else:
        print("="*60)
        print("UNIFIED OFFLINE WORKER & JOB RUNNER")
        print("="*60)
        print(f"Interval: {args.interval}s")
        print("running...")
        print("Press Ctrl+C to stop")
        print("="*60)
        asyncio.run(run_worker(interval_seconds=args.interval))
