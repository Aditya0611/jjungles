import time
import logging
import re
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

# Local imports
from models import (
    Config, ErrorCode, HASHTAG_CATEGORIES, INSTAGRAM_EXPLORE_URL,
    DELAY_PAGE_LOAD, TIMEOUT_PAGE_NAVIGATION
)
from observability import metrics

# Logger instance
logger = logging.getLogger(__name__)

def categorize_hashtag(hashtag: str) -> str:
    """Categorize a hashtag based on predefined keyword mappings."""
    hashtag_lower = hashtag.lower().lstrip('#')
    
    for category, keywords in HASHTAG_CATEGORIES.items():
        if any(keyword in hashtag_lower for keyword in keywords):
            return category
    
    return 'general'

def extract_hashtags_from_post(post_element) -> List[str]:
    """Extract hashtags from post caption/alt text."""
    hashtags = []
    try:
        # Check alt text first
        alt_text = post_element.get_attribute("alt")
        if alt_text:
            hashtags.extend(re.findall(r"#(\w+)", alt_text))
            
        # Check aria-label
        aria_label = post_element.get_attribute("aria-label")
        if aria_label:
            hashtags.extend(re.findall(r"#(\w+)", aria_label))
    except:
        pass
    return list(set(hashtags))

def scroll_page(page: Page, scroll_count: int = 15):
    """Scroll the page to load more content."""
    for i in range(scroll_count):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(1.5)
        logger.debug(f"Scroll {i+1}/{scroll_count} completed")

def discover_hashtags(page: Page) -> List[Dict[str, Any]]:
    """Discover trending hashtags from Instagram's Explore page."""
    logger.info("Starting hashtag discovery from Explore page")
    
    try:
        page.goto(INSTAGRAM_EXPLORE_URL, wait_until="networkidle", timeout=TIMEOUT_PAGE_NAVIGATION)
        time.sleep(DELAY_PAGE_LOAD)
        
        scroll_page(page, Config.SCROLL_COUNT)
        
        # Collect all posts
        post_elements = page.query_selector_all("article img, a[href*='/p/'] img")
        logger.info(f"Found {len(post_elements)} post elements to analyze")
        
        hashtag_counter = Counter()
        hashtag_samples = defaultdict(list)
        
        for post in post_elements[:Config.POSTS_TO_SCAN]:
            hashtags = extract_hashtags_from_post(post)
            for ht in hashtags:
                hashtag_counter[ht] += 1
                if len(hashtag_samples[ht]) < 3:
                    # Get post link if possible
                    try:
                        parent = post.query_selector("xpath=ancestor::a")
                        if parent:
                            link = parent.get_attribute("href")
                            if link:
                                hashtag_samples[ht].append(link)
                    except:
                        pass
                        
        # Filter and rank
        top_hashtags = []
        for hashtag, freq in hashtag_counter.most_common(Config.TOP_HASHTAGS_TO_SAVE):
            if freq >= Config.MIN_HASHTAG_FREQUENCY:
                category = categorize_hashtag(hashtag)
                top_hashtags.append({
                    'hashtag': hashtag,
                    'frequency': freq,
                    'category': category,
                    'posts_count': freq,
                    'sample_posts': hashtag_samples[hashtag]
                })
                
        logger.info(f"Discovered {len(top_hashtags)} hashtags above frequency threshold")
        metrics.gauge('discovered_hashtags_total', len(top_hashtags))
        
        return top_hashtags
        
    except Exception as e:
        logger.error(f"[{ErrorCode.SCRAPE_DISCOVERY_FAILED}] Discovery error: {e}")
        metrics.increment('discovery_failures_total')
        return []
