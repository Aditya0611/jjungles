import asyncio
import math
import os
import sys
import time
import traceback
from collections import Counter
from typing import Dict, List, Tuple, Optional

import orjson
from tabulate import tabulate

from src.config import get_config, Config
from src.scraper import scrape_locale, collect_channel_videos, _new_browser, _new_context, extract_hashtags_from_video, _parse_video_id
from src.sentiment import analyze_hashtag_sentiment
from src.supabase_storage import init_database, store_hashtags_batch, store_scraping_log
from src.dashboard import notify_dashboard
from src.logger import logger
from src.proxy import init_rotator


def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


async def run_scraper_pipeline(
    locales: str = "US",
    categories: str = "all",
    channels: Optional[str] = None,
    limit: Optional[int] = None,
    concurrency: Optional[int] = None,
    top_k: Optional[int] = None,
    headless: Optional[bool] = None,
    output_dir: Optional[str] = None,
) -> None:
    """
    Main entry point for the scraper pipeline.
    Orchestrates the scraping, processing, and storage of YouTube trend data.
    """
    start_time = time.time()
    logger.info("START: YouTube scraper pipeline initiated")

    try:
        cfg = get_config()

        # Apply Overrides
        if limit is not None:
            cfg.video_limit_per_locale = int(limit)
        if concurrency is not None:
            cfg.concurrency = int(concurrency)
        if top_k is not None:
            cfg.top_k = int(top_k)
        if headless is not None:
            cfg.headless = headless
        if output_dir is not None:
            cfg.output_dir = output_dir

        logger.info(f"Configuration: concurrency={cfg.concurrency}, headless={cfg.headless}, use_db={cfg.use_database}")

        # Initialize proxy rotator with strict mode
        logger.info(f"Initializing proxy rotator (strict_mode={cfg.proxy_strict_mode})...")
        try:
            init_rotator(cfg.proxy_list, strict_mode=cfg.proxy_strict_mode)
        except ValueError as e:
            logger.error(f"CRITICAL: Proxy initialization failed - {e}")
            logger.error("Scraper cannot proceed without proxies in strict mode.")
            sys.exit(1)

        # Initialize database if enabled
        if cfg.use_database:
            if not cfg.supabase_url:
                logger.warning("SUPABASE_URL not set")
            if not cfg.supabase_anon_key:
                logger.warning("SUPABASE_ANON_KEY not set")
            
            logger.info("Initializing database connection...")
            try:
                init_database()
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                logger.warning("Continuing without database storage...")
                cfg.use_database = False
        else:
            logger.info("Database storage is disabled via config.")

        # Setup collection lists
        all_hashtags: List[str] = []
        all_pairs: List[Tuple[str, str]] = []  # (video_id, hashtag)
        all_metadata: Dict[str, Dict] = {}  # video_id -> metadata

        # Task list
        scrape_tasks = []

        # 1. Channel Scraping
        if channels:
            await _scrape_channels(channels, cfg, all_pairs, all_metadata, all_hashtags)

        # 2. Trending Scraping
        target_locales = [x.strip() for x in locales.split(",") if x.strip()]
        target_categories = [x.strip().lower() for x in categories.split(",") if x.strip() and x.strip().lower() != "all"]
        
        if not target_categories:
            target_categories = [None] # type: ignore

        # Prepare tasks
        locale_sem = asyncio.Semaphore(2) # Limit concurrent locale scrapes

        async def protected_scrape(loc, cat):
            async with locale_sem:
                cat_str = f", category: {cat.upper()}" if cat else ""
                logger.info(f"Scraping trending hashtags: {loc}{cat_str}")
                try:
                    # No login required for trending
                    return await scrape_locale(loc, wait_for_login=False, category=cat, video_limit=cfg.video_limit_per_locale)
                except Exception as e:
                    logger.error(f"Error scraping {loc}/{cat}: {e}")
                    return [], {}

        for locale in target_locales:
            for category in target_categories:
                scrape_tasks.append(protected_scrape(locale, category))

        if scrape_tasks:
            logger.info(f"Starting {len(scrape_tasks)} trending scraping tasks...")
            results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Task failed: {res}")
                    continue
                if isinstance(res, tuple):
                    pairs, metadata = res
                    all_pairs.extend(pairs)
                    all_metadata.update(metadata)
                    for _, hashtag in pairs:
                        all_hashtags.append(hashtag)

        if not all_hashtags:
            logger.warning("No hashtags collected.")
            
            if cfg.proxy_strict_mode:
                if cfg.use_database:
                    store_scraping_log(
                        platform="youtube",
                        status="failure",
                        items_collected=0,
                        duration_seconds=time.time() - start_time,
                        metadata={"error": "Strict mode violation: No hashtags collected", "locales": target_locales}
                    )
                raise RuntimeError("Strict mode enabled: Pipeline completed with no results (likely blocked)")

            if cfg.use_database:
                store_scraping_log(
                    platform="youtube",
                    status="success_empty",
                    items_collected=0,
                    duration_seconds=time.time() - start_time,
                    metadata={"locales": target_locales, "categories": target_categories}
                )
            return

        # Process and Save Data
        await _process_and_save_data(
            all_hashtags, all_pairs, all_metadata, 
            cfg, target_locales, target_categories, start_time
        )

    except Exception as e:
        logger.error(f"Critical Pipeline Error: {e}")
        traceback.print_exc()
        if get_config().use_database:
            store_scraping_log(
                platform="youtube",
                status="failure",
                items_collected=0,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
        raise e


async def _scrape_channels(
    channels_str: str, 
    cfg: Config, 
    all_pairs: List, 
    all_metadata: Dict, 
    all_hashtags: List
) -> None:
    """Helper to handle channel scraping logic"""
    channel_ids = [x.strip() for x in channels_str.split(",") if x.strip()]
    logger.info(f"Scraping specific channels: {channel_ids}")

    async def scrape_channel_videos_helper(c_id):
        try:
            logger.info(f"Fetching videos for channel: {c_id}")
            urls = await collect_channel_videos(c_id, limit=cfg.video_limit_per_locale)
            logger.info(f"Found {len(urls)} videos for channel {c_id}")
            return urls
        except Exception as e:
            logger.error(f"Error scraping channel {c_id}: {e}")
            return []

    # Gather all URLs first
    channel_results = await asyncio.gather(
        *[scrape_channel_videos_helper(cid) for cid in channel_ids], 
        return_exceptions=True
    )
    
    channel_urls = []
    for res in channel_results:
        if isinstance(res, list):
            channel_urls.extend(res)
    
    if not channel_urls:
        return

    # Now scrape these URLs using Playwright
    unique_urls = list(set(channel_urls))
    logger.info(f"Processing {len(unique_urls)} channel videos...")
    
    pw, browser = await _new_browser()
    try:
        ctx = await _new_context(browser)
        processed = 0
        sem = asyncio.Semaphore(cfg.concurrency)
        
        async def process_video(url):
            nonlocal processed
            v_id = _parse_video_id(url)
            async with sem:
                page = await ctx.new_page()
                try:
                    tags, meta = await extract_hashtags_from_video(page, url)
                    if tags:
                        all_pairs.extend([(v_id, t) for t in tags])
                        all_metadata[v_id] = meta
                        all_hashtags.extend(tags)
                    processed += 1
                    if processed % 10 == 0:
                        logger.info(f"Channel Videos Processed: {processed}")
                except Exception as e:
                    logger.error(f"Error processing video {url}: {e}")
                finally:
                    await page.close()

        await asyncio.gather(*[process_video(u) for u in unique_urls], return_exceptions=True)
        await ctx.close()
    finally:
        await browser.close()
        await pw.stop()


async def _process_and_save_data(
    all_hashtags: List[str],
    all_pairs: List[Tuple[str, str]],
    all_metadata: Dict[str, Dict],
    cfg: Config,
    locales: List[str],
    categories: List[Optional[str]],
    start_time: float
) -> None:
    """Helper to aggregate stats, analyze sentiment, and save to DB/File"""
    
    # Aggregate top hashtags
    counter = Counter(all_hashtags)
    top_rows = counter.most_common(cfg.top_k)

    logger.info("Analyzing hashtags (sentiment & engagement)...")
    hashtag_stats: Dict[str, Dict] = {} 
    
    # Aggregate stats per hashtag
    for video_id, hashtag in all_pairs:
        if hashtag not in hashtag_stats:
            hashtag_stats[hashtag] = {
                "count": 0,
                "total_views": 0,
                "videos": [],
                "titles": [],
                "descriptions": []
            }
        
        hashtag_stats[hashtag]["count"] += 1
        hashtag_stats[hashtag]["videos"].append(video_id)
        
        # Get metadata for this video
        meta = all_metadata.get(video_id, {})
        if meta.get("views"):
            hashtag_stats[hashtag]["total_views"] += meta.get("views", 0)
        if meta.get("title"):
            hashtag_stats[hashtag]["titles"].append(meta["title"])
        if meta.get("description"):
            hashtag_stats[hashtag]["descriptions"].append(meta["description"])

    # Prepare database records
    db_records = []
    
    for hashtag, stats in hashtag_stats.items():
        # Calculate engagement score
        avg_views = stats["total_views"] / stats["count"] if stats["count"] > 0 else 0
        views_score = math.log10(avg_views + 1) * 10 
        frequency_score = min(stats["count"] * 5, 50) 
        engagement_score = min(views_score + frequency_score, 100.0)
        
        # Sentiment analysis
        # Use more titles and descriptions for richer context
        context_text = " ".join(stats["titles"][:5] + stats["descriptions"][:3])
        if not context_text.strip():
            context_text = hashtag
        
        sentiment_polarity, sentiment_label = analyze_hashtag_sentiment(hashtag, context_text)
        
        # Detailed metadata
        video_metadatas = []
        for video_id in stats["videos"][:10]:
            video_meta = all_metadata.get(video_id, {})
            if video_meta:
                video_metadatas.append(video_meta)
        
        total_likes = sum(m.get("likes", 0) or 0 for m in video_metadatas)
        total_comments = sum(m.get("comments", 0) or 0 for m in video_metadatas)
        avg_likes = total_likes / len(video_metadatas) if video_metadatas else 0
        avg_comments = total_comments / len(video_metadatas) if video_metadatas else 0
        
        channels = list(set([m.get("channel_name") for m in video_metadatas if m.get("channel_name")]))
        
        metadata_payload = {
            "video_count": stats["count"],
            "video_ids": stats["videos"][:10],
            "avg_views": int(avg_views),
            "total_views": stats["total_views"],
            "avg_likes": int(avg_likes),
            "total_likes": int(total_likes),
            "avg_comments": int(avg_comments),
            "total_comments": int(total_comments),
            "channels": channels[:5],
            "locales": list(set(locales)),
            "categories": list(set([c for c in categories if c])),
            "video_details": video_metadatas[:5] 
        }
        # Determine dominant language
        langs = [m.get("language") for m in video_metadatas if m.get("language") and m.get("language") != "unknown"]
        dominant_lang = Counter(langs).most_common(1)[0][0] if langs else "unknown"
        
        # Add language to metadata instead of separate column
        metadata_payload["language"] = dominant_lang

        if cfg.use_database:
            db_records.append((
                "youtube", 
                hashtag, 
                engagement_score,
                sentiment_polarity,
                sentiment_label,
                stats["count"],
                int(avg_views) if avg_views > 0 else None,
                int(total_likes) if total_likes > 0 else None,
                int(total_comments) if total_comments > 0 else None,
                metadata_payload,
                None
            ))

    # Store in database
    if cfg.use_database and db_records:
        logger.info(f"Storing {len(db_records)} hashtag records in Supabase...")
        try:
            store_hashtags_batch(db_records)
            logger.info("SUCCESS: Database storage completed")
        except Exception as e:
            logger.error(f"FAILURE: Database storage failed: {e}")

    # Output to files
    ensure_dir(cfg.output_dir)
    output_file = os.path.join(cfg.output_dir, "top_hashtags.json")
    with open(output_file, "wb") as f:
        f.write(orjson.dumps([{"hashtag": h, "count": c} for h, c in top_rows], option=orjson.OPT_INDENT_2))
    
    print(f"\n{'='*50}")
    print(tabulate(top_rows, headers=["Hashtag", "Count"], tablefmt="github"))
    print(f"{'='*50}")
    logger.info(f"Saved results to JSON: {output_file}")
    
    # Dashboard notification
    if cfg.dashboard_webhook_url:
        stats = {
            "total_hashtags": len(hashtag_stats),
            "total_videos": len(all_metadata),
            "top_hashtags": [{"hashtag": h, "count": c} for h, c in top_rows[:10]],
            "locales": locales,
            "categories": [c for c in categories if c],
            "timestamp": os.getenv("TIMESTAMP", ""),
        }
        try:
            await notify_dashboard(stats, cfg.dashboard_webhook_url)
        except Exception as e:
            logger.error(f"Failed to notify dashboard: {e}")

    # Log completion
    if cfg.use_database:
        store_scraping_log(
            platform="youtube",
            status="success",
            items_collected=len(db_records),
            duration_seconds=time.time() - start_time,
            metadata={"locales": locales, "categories": categories}
        )
