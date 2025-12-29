#!/usr/bin/env python3
"""
APScheduler-based Worker for Social Media Scraper
Lightweight, in-process scheduler that manages scraper jobs based on database settings.
"""

import os
import logging
import asyncio
import signal
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("APSchedulerWorker")

# Import scraper core
try:
    from base import run_scraper, init_supabase, SUPABASE_URL, SUPABASE_KEY
except ImportError as e:
    logger.error(f"Failed to import scraper core: {e}")
    run_scraper = None
    init_supabase = None

class APSchedulerWorker:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.supabase = None
        self.platforms_config = {}
        self.running = False
        self.reload_interval = int(os.environ.get("WORKER_RELOAD_INTERVAL", "300"))

    async def initialize(self):
        """Initialize worker and Supabase client."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("Supabase credentials missing. Set SUPABASE_URL and SUPABASE_KEY.")
            return False
            
        self.supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
        if not self.supabase:
            logger.error("Failed to initialize Supabase client.")
            return False
            
        logger.info("Worker initialized successfully.")
        return True

    def _get_job_id(self, platform):
        """Generate a consistent job ID for a platform."""
        return f"scraper_{platform.lower()}"

    async def run_platform_job(self, platform, region, headless, upload_to_db):
        """Job wrapper to run the scraper for a platform."""
        logger.info(f"Triggering scheduled run for {platform}...")
        
        if not run_scraper:
            logger.error("Scraper core not available.")
            return

        try:
            # Set worker context env var
            os.environ["OS_SCRAPER_WORKER"] = "true"
            
            # Run the scraper
            results = await run_scraper(
                platform=platform,
                region=region,
                headless=headless,
                debug=False,
                upload_to_db=upload_to_db
            )
            
            count = len(results) if results else 0
            logger.info(f"Scheduled run for {platform} completed: {count} items.")
            
            # Update success stats via RPC if possible
            try:
                self.supabase.rpc("update_run_stats", {
                    "p_platform": platform.lower(),
                    "p_success": count > 0
                }).execute()
            except Exception as e:
                logger.debug(f"Could not update stats via RPC: {e}")
                
        except Exception as e:
            logger.error(f"Job for {platform} failed: {e}", exc_info=True)
        finally:
            if "OS_SCRAPER_WORKER" in os.environ:
                del os.environ["OS_SCRAPER_WORKER"]

    async def sync_jobs_with_db(self):
        """Fetch settings from DB and update scheduler jobs."""
        logger.info("Syncing jobs with database settings...")
        
        try:
            # Query scheduler_settings table
            result = self.supabase.table("scheduler_settings").select("*").execute()
            
            if not result.data:
                logger.warning("No platform settings found in scheduler_settings table.")
                return

            current_job_ids = [job.id for job in self.scheduler.get_jobs()]
            target_platforms = []

            for config in result.data:
                platform = config.get("platform")
                enabled = config.get("enabled", False)
                frequency = float(config.get("frequency_hours", 3.0))  # Default 3 hours (between 2-4)
                metadata = config.get("metadata", {})
                job_id = self._get_job_id(platform)
                
                # NEW: Validate frequency range (0.5-24 hours)
                if frequency < 0.5:
                    logger.warning(f"Frequency {frequency}h too low for {platform}, using minimum 0.5h")
                    frequency = 0.5
                elif frequency > 24:
                    logger.warning(f"Frequency {frequency}h too high for {platform}, using maximum 24h")
                    frequency = 24
                
                if not enabled:
                    # Remove if disabled
                    if job_id in current_job_ids:
                        self.scheduler.remove_job(job_id)
                        logger.info(f"🔴 Removed job for disabled platform: {platform}")
                    continue

                target_platforms.append(platform)
                
                # Setup parameters
                job_args = [
                    platform,
                    metadata.get("region", "en"),
                    metadata.get("headless", True),
                    metadata.get("upload_to_db", True)
                ]
                
                # Check if job exists and update if frequency changed
                existing_job = self.scheduler.get_job(job_id)
                if existing_job:
                    # Check if interval changed (simple check)
                    # Note: frequency is hours, IntervalTrigger uses seconds/hours/etc.
                    trigger = IntervalTrigger(hours=frequency)
                    # Comparison is simplified here
                    self.scheduler.reschedule_job(job_id, trigger=trigger)
                    # Update args in case they changed
                    self.scheduler.modify_job(job_id, args=job_args)
                    logger.info(f"🔄 Updated existing job for {platform} (frequency: {frequency}h)")
                else:
                    # Add new job
                    self.scheduler.add_job(
                        self.run_platform_job,
                        trigger=IntervalTrigger(hours=frequency),
                        args=job_args,
                        id=job_id,
                        name=f"Scrape {platform}",
                        replace_existing=True,
                        next_run_time=datetime.now() + timedelta(seconds=10) # Run soon after start
                    )
                    logger.info(f"✅ Added new job for {platform} (frequency: {frequency}h, next run: ~10s)")

            # Cleanup removed platforms
            target_job_ids = [self._get_job_id(p) for p in target_platforms]
            for j_id in current_job_ids:
                if j_id.startswith("scraper_") and j_id not in target_job_ids:
                    self.scheduler.remove_job(j_id)
                    logger.info(f"🗑️  Cleaned up obsolete job: {j_id}")
            
            # Log summary
            active_jobs = len(self.scheduler.get_jobs())
            logger.info(f"📊 Sync complete: {active_jobs} active jobs for platforms: {', '.join(target_platforms)}")

        except Exception as e:
            logger.error(f"Error syncing jobs: {e}")

    async def run(self):
        """Main worker loop."""
        if not await self.initialize():
            return

        self.scheduler.start()
        self.running = True
        logger.info("APScheduler started.")

        # Initial sync
        await self.sync_jobs_with_db()

        try:
            while self.running:
                # Periodic sync with database
                await asyncio.sleep(self.reload_interval)
                await self.sync_jobs_with_db()
        except asyncio.CancelledError:
            logger.info("Worker sync loop cancelled.")
        finally:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler shut down.")

    def stop(self, *args):
        """Stop the worker."""
        logger.info("Shutdown signal received...")
        self.running = False

async def main():
    """Main entry point for the worker process."""
    worker = APSchedulerWorker()
    
    # Handle signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # On Windows, signal handler via loop is not fully supported for all signals
            pass

    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
