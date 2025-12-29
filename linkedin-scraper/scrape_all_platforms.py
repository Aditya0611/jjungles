"""
Cross-Platform Hashtag Scraper - Main Entry Point
Supports LinkedIn (full), Instagram, Twitter, TikTok, Facebook (stubs)
"""

import argparse
import json
from platform_manager import PlatformManager


def main():
    """Main entry point for cross-platform scraping"""
    parser = argparse.ArgumentParser(
        description='Cross-Platform Hashtag Scraper - LinkedIn, Instagram, Twitter, TikTok, Facebook'
    )
    parser.add_argument(
        '--platforms',
        nargs='+',
        choices=['linkedin', 'instagram', 'twitter', 'tiktok', 'facebook', 'all'],
        default=['linkedin'],
        help='Platforms to scrape (default: linkedin)'
    )
    parser.add_argument(
        '--max-scrolls',
        type=int,
        default=30,
        help='Maximum number of scrolls per platform (default: 30)'
    )
    parser.add_argument(
        '--scroll-pause',
        type=float,
        default=2.0,
        help='Pause time between scrolls in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--no-supabase',
        action='store_true',
        help='Disable Supabase saving'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (LinkedIn only)'
    )
    
    args = parser.parse_args()
    
    # Determine platforms to scrape
    if 'all' in args.platforms:
        platforms = ['linkedin', 'instagram', 'twitter', 'tiktok', 'facebook']
    else:
        platforms = args.platforms
    
    # Initialize platform manager
    use_supabase = not args.no_supabase
    manager = PlatformManager(use_supabase=use_supabase)
    
    print("="*70)
    print("🌐 CROSS-PLATFORM HASHTAG SCRAPER")
    print("="*70)
    print(f"📋 Platforms to scrape: {', '.join(platforms)}")
    print(f"📊 Max scrolls per platform: {args.max_scrolls}")
    print(f"⏱️  Scroll pause time: {args.scroll_pause}s")
    print(f"💾 Supabase enabled: {use_supabase}")
    print("="*70)
    
    # Scrape each platform
    results = manager.scrape_multiple_platforms(
        platforms,
        max_scrolls=args.max_scrolls,
        scroll_pause_time=args.scroll_pause,
        headless=args.headless
    )
    
    # Get combined results
    if results:
        combined = manager.get_combined_results()
        
        # Save combined results
        with open('combined_results.json', 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*70)
        print("📊 COMBINED RESULTS ACROSS ALL PLATFORMS")
        print("="*70)
        print(f"Platforms scraped: {', '.join(combined.get('platforms_scraped', []))}")
        
        stats = combined.get('combined_statistics', {})
        print(f"Total hashtags: {stats.get('total_hashtags_across_platforms', 0)}")
        print(f"Unique hashtags: {stats.get('total_unique_hashtags', 0)}")
        
        top_hashtags = combined.get('top_20_cross_platform_hashtags', [])
        if top_hashtags:
            print("\n🔥 TOP 20 CROSS-PLATFORM HASHTAGS:")
            for i, item in enumerate(top_hashtags[:20], 1):
                platform = item.get('platform', 'unknown')
                hashtag = item.get('hashtag', 'N/A')
                count = item.get('count', 0)
                print(f"{i:2d}. [{platform:8s}] {hashtag:30s} - {count:3d} occurrences")
        
        print(f"\n💾 Combined results saved to: combined_results.json")
    else:
        print("\n❌ No results collected from any platform")
    
    print("\n✅ Scraping complete!")


if __name__ == "__main__":
    main()

