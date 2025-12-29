import asyncio
import random
import re
import time
from typing import Dict, List, Optional, Tuple

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from langdetect import detect, LangDetectException

from .config import get_config
from .utils import unique_preserve_order, choose_user_agent
from .logger import logger
from .proxy import get_proxy

# YouTube category mappings
YOUTUBE_CATEGORIES = {
	"music": "4gINGgt5dG1hX2NoYXJ0cw%3D%3D",
	"gaming": "gaming",
	"sports": "4gIcGhpnYW1pbmdfY29uc3VtZXJz",
	"news": "4gIKGhphdmFzY3JpcHRlcg%3D%3D",
	"movies": "4gI0ChhldmVudHM",
	"tv": "4gIKGhphdmFzY3JpcHRlcg%3D%3D",
}
VIDEO_ID_RE = re.compile(r"(?:v=|/shorts/|/watch/|youtu\.be/)([A-Za-z0-9_-]{11})")
VALID_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
CONSENT_SELECTORS = [
	'button:has-text("I agree")',
	'button:has-text("Accept all")',
	'button:has-text("AGREE")',
	'#introAgreeButton',
]

async def _sleep_jitter(low: float = 0.2, high: float = 0.8) -> None:
	await asyncio.sleep(random.uniform(low, high))

async def _new_browser():
    cfg = get_config()
    logger.info("Initializing Playwright browser...")
    launch_kwargs = {
        "headless": cfg.headless,
        "timeout": cfg.navigation_timeout_ms,
    }
    proxy_url = get_proxy() or getattr(cfg, "proxy_server", None)
    if proxy_url:
        logger.info(f"Using proxy for browser: {proxy_url}")
        launch_kwargs["proxy"] = {"server": proxy_url}
    elif cfg.proxy_strict_mode:
        error_msg = "PROXY ENFORCEMENT FAILURE: No proxy available for browser initialization in strict mode."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(**launch_kwargs)
    logger.info("Browser launched successfully")
    return pw, browser

async def _new_context(browser: Browser) -> BrowserContext:
    cfg = get_config()
    ua = choose_user_agent(cfg.user_agents_list)
    ctx = await browser.new_context(
        user_agent=ua,
        viewport={"width": 1366, "height": 768},
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        await ctx.add_cookies([{
            "name": "CONSENT", "value": "YES+", "domain": ".youtube.com", "path": "/"
        }])
    except Exception as e:
        logger.debug(f"Failed to add consent cookie: {e}")
    return ctx

async def collect_trending_video_urls_api(limit: int, locale: str, category: Optional[str] = None) -> List[str]:
    """
    Collect trending video URLs using YouTube Data API v3 and aiohttp.
    """
    cfg = get_config()
    if not cfg.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY is required.")
    
    base_url = "https://www.googleapis.com/youtube/v3/videos"
    video_urls = []
    next_page_token = None
    total_fetched = 0
    
    logger.info(f"Fetching trending videos via API (region: {locale})...")
    
    async with aiohttp.ClientSession() as session:
        while total_fetched < limit:
            params = {
                'key': cfg.youtube_api_key,
                'chart': 'mostPopular',
                'regionCode': locale,
                'part': 'id',
                'maxResults': min(limit - total_fetched, 50),
            }
            if next_page_token:
                params['pageToken'] = next_page_token
            
            try:
                # Retry loop for specific request with proxy rotation
                data = None
                for attempt in range(cfg.max_retries):
                    current_proxy = get_proxy() or getattr(cfg, "proxy_server", None)
                    if current_proxy:
                         logger.info(f"Using proxy {current_proxy} (Attempt {attempt+1})")
                    
                    try:
                        async with session.get(base_url, params=params, proxy=current_proxy, timeout=cfg.request_timeout_seconds) as response:
                             response.raise_for_status()
                             data = await response.json()
                             break # Success
                    except Exception as req_err:
                        logger.warning(f"Request failed (attempt {attempt+1}): {req_err}")
                        if attempt == cfg.max_retries - 1: raise req_err
                        await asyncio.sleep(2 ** attempt) # Exponential backoff
                
                if not data:
                    break

                items = data.get('items', [])
                for item in items:
                    video_id = item.get('id')
                    if video_id:
                        video_urls.append(f'https://www.youtube.com/watch?v={video_id}')
                        total_fetched += 1
                
                logger.info(f"Fetched {len(items)} videos ({total_fetched}/{limit})")
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token or total_fetched >= limit:
                    break
            except Exception as e:
                logger.error(f"Error fetching videos: {e}")
                raise

    logger.info(f"Collected {len(video_urls)} URLs via API")
    return video_urls[:limit]

async def collect_channel_videos(channel_id: str, limit: int = 50) -> List[str]:
    """
    Fetch recent videos from a specific channel using YouTube API.
    """
    cfg = get_config()
    if not cfg.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY is required.")
        
    base_url = "https://www.googleapis.com/youtube/v3/search"
    video_urls = []
    next_page_token = None
    
    proxy_url = get_proxy() or getattr(cfg, "proxy_server", None)
    
    logger.info(f"Fetching recent videos for channel {channel_id}...")
    
    async with aiohttp.ClientSession() as session:
        while len(video_urls) < limit:
            params = {
                'key': cfg.youtube_api_key,
                'channelId': channel_id,
                'part': 'id',
                'order': 'date',
                'maxResults': min(limit - len(video_urls), 50),
                'type': 'video'
            }
            if next_page_token:
                params['pageToken'] = next_page_token

            try:
                data = None
                for attempt in range(3):
                    current_proxy = get_proxy() or getattr(cfg, "proxy_server", None)
                    try:
                        async with session.get(base_url, params=params, proxy=current_proxy, timeout=cfg.request_timeout_seconds) as response:
                            response.raise_for_status()
                            data = await response.json()
                            break
                    except Exception as req_err:
                        logger.warning(f"Channel fetch failed (attempt {attempt+1}): {req_err}")
                        if attempt == 2: raise req_err
                        await asyncio.sleep(2 ** attempt)

                if not data:
                    break
                    
                items = data.get('items', [])
                for item in items:
                    vid = item.get('id', {}).get('videoId')
                    if vid:
                        video_urls.append(f"https://www.youtube.com/watch?v={vid}")
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching channel videos: {e}")
                break
                
    return video_urls

async def collect_trending_video_urls(page: Page, limit: int, locale: str, wait_for_login: bool = False, category: Optional[str] = None) -> List[str]:
    return await collect_trending_video_urls_api(limit, locale, category)

def _parse_video_id(url: str) -> Optional[str]:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else None

def _normalize_to_watch_url(url: str) -> Optional[str]:
    vid = _parse_video_id(url)
    return f"https://www.youtube.com/watch?v={vid}" if vid else None

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=6))
async def extract_hashtags_from_video(page: Page, video_url: str) -> Tuple[List[str], Dict]:
    normalized = _normalize_to_watch_url(video_url) or video_url
    metadata = {
        "video_id": _parse_video_id(video_url),
        "url": normalized,
        "title": None, "description": None, "views": None,
        "likes": None, "comments": None, "channel_name": None,
        "upload_date": None, "language": None
    }
    
    try:
        await page.goto(normalized, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        cfg = get_config()
        if cfg.proxy_strict_mode:
            raise RuntimeError(f"Strict mode enabled: Navigation failed for {normalized}: {e}") from e
        return [], metadata

    # Handle consent
    try:
        # Check if consent dialog is widely visible
        for sel in CONSENT_SELECTORS:
            if await page.is_visible(sel):
                await page.click(sel)
                await page.wait_for_timeout(1000)
                break
    except Exception as e:
        logger.debug(f"Consent handling ignored: {e}")
    
    await page.wait_for_timeout(2000)

    # Scrape Metadata
    try:
        # Title
        try:
             # Try multiple common selectors for title
             selectors = ["h1.ytd-watch-metadata", "h1.title", "#title h1", ".ytd-video-primary-info-renderer h1", "meta[name='title']"]
             for sel in selectors:
                 try:
                     if sel.startswith("meta"):
                         metadata["title"] = await page.get_attribute(sel, "content", timeout=2000)
                     else:
                         metadata["title"] = await page.inner_text(sel, timeout=3000)
                     if metadata["title"]:
                         break
                 except Exception:
                     continue
             
             if not metadata["title"]:
                 logger.warning(f"Title extraction failed for {video_url} after trying all selectors")
        except Exception as e:
             logger.warning(f"Title extraction failed: {e}")
        
        # Description
        try:
            # Click "more" if available to expand description
            more_btn = await page.query_selector("#expand, .more-button, #action-panel-details")
            if more_btn and await more_btn.is_visible():
                await more_btn.click()
                await page.wait_for_timeout(500)
            
            desc_selectors = [
                "#description-inline-expander .ytd-text-inline-expander",
                "#description-inline-expander",
                "#description.ytd-video-secondary-info-renderer",
                "#content.ytd-expander",
                "meta[name='description']"
            ]
            
            for sel in desc_selectors:
                try:
                    if sel.startswith("meta"):
                        metadata["description"] = await page.get_attribute(sel, "content", timeout=2000)
                    else:
                        metadata["description"] = await page.inner_text(sel, timeout=2000)
                    if metadata["description"]:
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Description extraction failed: {e}")

        # Channel Name
        try:
            channel_el = await page.query_selector("ytd-channel-name #text a")
            if channel_el:
                metadata["channel_name"] = await channel_el.inner_text()
        except Exception as e:
            logger.debug(f"Channel name extraction failed: {e}")
            
        # Views
        try:
            views_text = await page.inner_text("#count .ytd-video-view-count-renderer span.view-count", timeout=2000)
            # Clean string like "1,234 views" -> 1234
            if views_text:
                clean_views = re.sub(r'[^0-9]', '', views_text)
                if clean_views:
                    metadata["views"] = int(clean_views)
        except Exception as e:
            logger.debug(f"Views extraction failed: {e}")

        # Likes (approximate, often in aria-label)
        try:
            # This segment selector is fragile as YouTube changes it often. 
            # Trying common variations.
            like_btn = await page.query_selector("like-button-view-model button")
            if like_btn:
               label = await like_btn.get_attribute("aria-label")
               if label:
                   # Extract numbers from "like this video along with 1,234 other people"
                   clean_likes = re.sub(r'[^0-9]', '', label)
                   if clean_likes:
                       metadata["likes"] = int(clean_likes)
        except Exception as e:
            logger.debug(f"Likes extraction failed: {e}")

        # Comments Count
        try:
            # Scroll down a bit to trigger comments loading
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1000)
            
            comments_el = await page.query_selector("ytd-comments-header-renderer #count .count-text")
            if not comments_el:
                 comments_el = await page.query_selector("#comments #count .count-text")
            
            if comments_el:
                c_text = await comments_el.inner_text()
                if c_text:
                    clean_comments = re.sub(r'[^0-9]', '', c_text)
                    if clean_comments:
                        metadata["comments"] = int(clean_comments)
        except Exception as e:
            logger.debug(f"Comments extraction failed: {e}")
        
        # Upload Date
        try:
            date_el = await page.query_selector("meta[itemprop='uploadDate']")
            if date_el:
                content = await date_el.get_attribute("content")
                if content:
                    metadata["upload_date"] = content
        except Exception as e:
            logger.debug(f"Upload date extraction failed: {e}")

        # Keywords / Tags
        try:
            tags_el = await page.query_selector("meta[name='keywords']")
            if tags_el:
                content = await tags_el.get_attribute("content")
                if content:
                    metadata["tags"] = [t.strip() for t in content.split(",") if t.strip()]
        except Exception as e:
            logger.debug(f"Tags extraction failed: {e}")

        # Language Detection
        text_content = (metadata.get("title") or "") + " " + (metadata.get("description") or "")
        if text_content.strip():
            try:
                metadata["language"] = detect(text_content)
            except LangDetectException:
                metadata["language"] = "unknown"

    except Exception as e:
        logger.warning(f"Partial metadata extraction failure for {video_url}: {e}")

    # Extract hashtags from anchors
    anchors = await page.eval_on_selector_all(
        'a[href^="/hashtag/"]',
        "els => els.map(e => e.textContent.trim()).filter(Boolean)"
    )
    hashtags = [a[1:] if a.startswith("#") else a for a in anchors]
    
    return unique_preserve_order(hashtags), metadata

async def scrape_locale(locale: str, wait_for_login: bool = False, category: Optional[str] = None, video_limit: Optional[int] = None) -> Tuple[List[Tuple[str, str]], Dict[str, Dict]]:
    cfg = get_config()
    limit = video_limit if video_limit is not None else cfg.video_limit_per_locale
    
    logger.info(f"Fetching trending video URLs for locale: {locale}...")
    try:
        urls = await collect_trending_video_urls_api(limit, locale, category)
    except Exception as e:
        logger.error(f"Failed to fetch videos: {e}")
        if cfg.proxy_strict_mode:
            raise RuntimeError(f"Strict mode enabled: Failed to fetch videos for {locale}: {e}") from e
        return [], {}

    if not urls:
        return [], {}

    logger.info(f"Processing {len(urls)} videos with Playwright...")
    pw, browser = await _new_browser()
    try:
        ctx = await _new_context(browser)
        results = []
        video_metadata = {}
        processed = 0
        
        # Use concurrency for video details
        sem = asyncio.Semaphore(cfg.concurrency)
        
        async def process(url):
            nonlocal processed
            v_id = _parse_video_id(url)
            async with sem:
                page = await ctx.new_page()
                try:
                    tags, meta = await extract_hashtags_from_video(page, url)
                    if tags:
                        results.extend([(v_id, t) for t in tags])
                        video_metadata[v_id] = meta
                    processed += 1
                    if processed % 10 == 0:
                        logger.info(f"Processed {processed}/{len(urls)} videos")
                except Exception as e:
                    logger.error(f"Error processing {v_id}: {e}")
                finally:
                    await page.close()

        await asyncio.gather(*[process(u) for u in urls], return_exceptions=True)
        await ctx.close()
        return results, video_metadata
    finally:
        await browser.close()
        await pw.stop()
