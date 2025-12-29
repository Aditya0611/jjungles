"""
Platform Manager for Cross-Platform Hashtag Scraping
Manages multiple platform scrapers (LinkedIn, Instagram, Twitter, etc.)
"""

from typing import Dict, List, Optional
from base_scraper import BaseHashtagScraper
import importlib


class PlatformManager:
    """Manages multiple platform scrapers"""
    
    SUPPORTED_PLATFORMS = {
        'linkedin': 'linkedin_hashtag_scraper_playwright',
    }
    
    def __init__(self, use_supabase: bool = True):
        """
        Initialize platform manager
        
        Args:
            use_supabase: Whether to save data to Supabase
        """
        self.use_supabase = use_supabase
        self.scrapers: Dict[str, BaseHashtagScraper] = {}
        self.results: Dict[str, Dict] = {}
    
    def get_scraper(self, platform: str) -> Optional[BaseHashtagScraper]:
        """
        Get or create a scraper for the specified platform
        
        Args:
            platform: Platform name (linkedin, instagram, twitter, etc.)
            
        Returns:
            Scraper instance or None if platform not supported
        """
        platform = platform.lower()
        
        if platform not in self.SUPPORTED_PLATFORMS:
            print(f"❌ Platform '{platform}' is not supported.")
            print(f"   Supported platforms: {', '.join(self.SUPPORTED_PLATFORMS.keys())}")
            return None
        
        # Return existing scraper if already created
        if platform in self.scrapers:
            return self.scrapers[platform]
        
        # Try to import and create scraper
        try:
            module_name = self.SUPPORTED_PLATFORMS[platform]
            # Dynamic import
            module = importlib.import_module(module_name)
            scraper_class = getattr(module, f'{platform.capitalize()}HashtagScraper')
            scraper = scraper_class(use_supabase=self.use_supabase)
            self.scrapers[platform] = scraper
            return scraper
        except ImportError as e:
            print(f"⚠️  Platform '{platform}' module not found: {e}")
            print(f"   Creating stub scraper for {platform}")
            # Create a stub scraper
            from stub_scrapers import create_stub_scraper
            scraper = create_stub_scraper(platform, use_supabase=self.use_supabase)
            self.scrapers[platform] = scraper
            return scraper
        except Exception as e:
            print(f"❌ Error creating scraper for '{platform}': {e}")
            return None
    
    def scrape_platform(self, platform: str, **kwargs) -> Optional[Dict]:
        """
        Scrape hashtags from a specific platform
        
        Args:
            platform: Platform name
            **kwargs: Platform-specific arguments (max_scrolls, etc.)
            
        Returns:
            Results dictionary or None if scraping failed
        """
        scraper = self.get_scraper(platform)
        if not scraper:
            return None
        
        try:
            print(f"\n🚀 Starting {platform.upper()} scraping...")
            
            # Start scraper (initializes browser/proxies for Playwright scrapers)
            if hasattr(scraper, 'start'):
                scraper.start()
                
            # Login (platform-specific)
            scraper.login(**kwargs)
            
            # Navigate to feed
            scraper.navigate_to_feed()
            
            # Scrape hashtags
            max_scrolls = kwargs.get('max_scrolls', 30)
            scroll_pause_time = kwargs.get('scroll_pause_time', 2.0)
            scraper.scroll_and_collect_hashtags(max_scrolls=max_scrolls, scroll_pause_time=scroll_pause_time)
            
            # Print and save results
            scraper.print_results()
            results, records_inserted = scraper.save_results()
            
            # Save dashboard data (reusing results to avoid duplicate inserts)
            if hasattr(scraper, 'save_dashboard_data'):
                scraper.save_dashboard_data(results=results)
            
            self.results[platform] = results
            return results
            
        except Exception as e:
            print(f"❌ Error scraping {platform}: {e}")
            return None
        finally:
            # Close scraper
            try:
                scraper.close()
            except:
                pass
    
    def scrape_multiple_platforms(self, platforms: List[str], **kwargs) -> Dict[str, Dict]:
        """
        Scrape hashtags from multiple platforms
        
        Args:
            platforms: List of platform names
            **kwargs: Platform-specific arguments
            
        Returns:
            Dictionary mapping platform names to results
        """
        all_results = {}
        
        for platform in platforms:
            result = self.scrape_platform(platform, **kwargs)
            if result:
                all_results[platform] = result
        
        return all_results
    
    def get_combined_results(self) -> Dict:
        """
        Get combined results from all scraped platforms
        
        Returns:
            Combined results dictionary
        """
        if not self.results:
            return {}
        
        # Combine top hashtags from all platforms
        all_top_hashtags = []
        total_hashtags = 0
        total_unique = 0
        
        for platform, results in self.results.items():
            if 'top_10_trending_hashtags' in results:
                for hashtag_data in results['top_10_trending_hashtags']:
                    all_top_hashtags.append({
                        'platform': platform,
                        **hashtag_data
                    })
            
            if 'statistics' in results:
                total_hashtags += results['statistics'].get('total_hashtags_collected', 0)
                total_unique += results['statistics'].get('unique_hashtags', 0)
        
        # Sort by count across all platforms
        all_top_hashtags.sort(key=lambda x: x.get('count', 0), reverse=True)
        
        return {
            'platforms_scraped': list(self.results.keys()),
            'combined_statistics': {
                'total_hashtags_across_platforms': total_hashtags,
                'total_unique_hashtags': total_unique,
                'platforms_count': len(self.results)
            },
            'top_20_cross_platform_hashtags': all_top_hashtags[:20],
            'platform_results': self.results
        }
    
    def list_supported_platforms(self) -> List[str]:
        """Return list of supported platforms"""
        return list(self.SUPPORTED_PLATFORMS.keys())

