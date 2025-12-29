import argparse
import asyncio
import sys
import traceback
from src.logger import logger
from src.pipeline import run_scraper_pipeline

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
    except Exception:
        pass

def parse_args():
    parser = argparse.ArgumentParser(description="YouTube Trending Hashtags Scraper")
    parser.add_argument("--locales", type=str, default="US", help="Comma-separated locales, e.g., US,IN,GB")
    parser.add_argument("--categories", type=str, default="all", help="Comma-separated categories: music,gaming,sports,news,movies,tv or 'all' for all categories")
    parser.add_argument("--channels", type=str, default=None, help="Comma-separated channel IDs to scrape")
    parser.add_argument("--limit", type=int, default=None, help="Override per-locale/channel video limit")
    parser.add_argument("--concurrency", type=int, default=None, help="Override concurrency")
    parser.add_argument("--top", type=int, default=None, help="Top K hashtags to display/export")
    parser.add_argument("--headless", type=str, default=None, help="true/false to override headless")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Parse headless arg logic
    headless_val = None
    if args.headless is not None:
        headless_val = (args.headless.lower() == "true")

    try:
        await run_scraper_pipeline(
            locales=args.locales,
            categories=args.categories,
            channels=args.channels,
            limit=args.limit,
            concurrency=args.concurrency,
            top_k=args.top,
            headless=headless_val,
            output_dir=args.output
        )
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled Error: {e}")
        traceback.print_exc()
        sys.exit(1)

