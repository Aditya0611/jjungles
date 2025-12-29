"""
Stub Scrapers for Platforms Not Yet Fully Implemented
These provide placeholder implementations for Sprint 1
"""

from base_scraper import BaseHashtagScraper
from typing import List, Tuple
import time


def create_stub_scraper(platform: str, use_supabase: bool = True) -> BaseHashtagScraper:
    """Create a stub scraper for a platform"""
    
    class StubScraper(BaseHashtagScraper):
        """Stub implementation for platforms not yet fully implemented"""
        
        def __init__(self, platform_name: str, use_supabase: bool = True):
            super().__init__(platform_name, use_supabase)
            self.is_stub = True
        
        def login(self, **kwargs):
            """Stub login - not implemented yet"""
            print(f"⚠️  {self.platform_name.upper()} scraper is a STUB - login not implemented")
            print(f"   This platform will be fully implemented in a future sprint")
            time.sleep(1)  # Simulate login delay
        
        def navigate_to_feed(self):
            """Stub navigate - not implemented yet"""
            print(f"⚠️  {self.platform_name.upper()} scraper is a STUB - navigation not implemented")
            time.sleep(1)
        
        def scroll_and_collect_hashtags(self, max_scrolls: int = 30, scroll_pause_time: float = 2.0):
            """Stub scraping - returns empty results"""
            print(f"⚠️  {self.platform_name.upper()} scraper is a STUB - scraping not implemented")
            print(f"   Returning empty results. Full implementation coming soon.")
            self.scroll_count = 0
            self.hashtags = []
            self.posts_scanned = 0
        
        def close(self):
            """Stub close - nothing to close"""
            pass
    
    return StubScraper(platform, use_supabase)


# Platform-specific stub classes
class InstagramHashtagScraper(create_stub_scraper('instagram').__class__):
    """Instagram scraper stub - to be implemented"""
    pass


class TwitterHashtagScraper(create_stub_scraper('twitter').__class__):
    """Twitter/X scraper stub - to be implemented"""
    pass


class TikTokHashtagScraper(create_stub_scraper('tiktok').__class__):
    """TikTok scraper stub - to be implemented"""
    pass


class FacebookHashtagScraper(create_stub_scraper('facebook').__class__):
    """Facebook scraper stub - to be implemented"""
    pass

