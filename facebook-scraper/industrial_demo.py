#!/usr/bin/env python3
"""
Industrial Facebook Scraper Demo - All Categories
==================================================

Automatically scrapes ALL categories from config/categories.json:
- No prompts - runs all categories automatically
- Sequential processing
- Comprehensive metrics
- Advanced rate limiting
- Proxy rotation
- Session persistence
- Advanced anti-detection
"""

import sys
import uuid
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from industrial_scraper import IndustrialFacebookScraper, create_industrial_scraper

def load_categories():
    """Load all categories from config file"""
    config_path = Path(__file__).parent / "config" / "categories.json"
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        categories_data = json.load(f)
    
    return list(categories_data.keys())

def main():
    """Run industrial scraping demo for ALL categories"""
    
    print("=" * 80)
    print("Industrial Facebook Scraper - All Categories")
    print("=" * 80)
    print()
    print("Features:")
    print("  ✓ Automatic processing of ALL categories")
    print("  ✓ Advanced rate limiting (token bucket algorithm)")
    print("  ✓ Enhanced proxy management with health checks")
    print("  ✓ Session persistence and rotation")
    print("  ✓ Advanced anti-detection (fingerprinting evasion)")
    print("  ✓ Real-time metrics and monitoring")
    print()
    
    # Load all categories
    all_categories = load_categories()
    if not all_categories:
        print("❌ No categories found in config/categories.json")
        return 1
    
    print(f"Found {len(all_categories)} categories: {', '.join(all_categories)}")
    print()
    
    # Ask for single category test or all categories
    print("Test Options:")
    print("  1. Test single category (recommended for testing)")
    print("  2. Run all categories")
    print()
    choice = input("Choose option (1 or 2, default 1): ").strip() or "1"
    
    if choice == "1":
        # Single category test
        print()
        print("Available categories:", ", ".join(all_categories))
        category_input = input("Enter category name to test: ").strip().lower()
        
        if category_input not in all_categories:
            print(f"❌ Invalid category. Using 'technology' as default.")
            category_input = "technology"
        
        categories = [category_input]
        print(f"\n✓ Testing single category: {category_input}")
    else:
        # All categories
        categories = all_categories
        print(f"\n✓ Running all {len(categories)} categories")
    
    print()
    
    # Configuration
    max_posts = input("Max posts per category (default 100): ").strip()
    max_posts = int(max_posts) if max_posts.isdigit() else 100
    
    use_proxies = True
    use_sessions = True
    rate_limit = 30
    
    print()
    print("Configuration:")
    print(f"  Categories: {len(categories)} ({', '.join(categories)})")
    print(f"  Max posts per category: {max_posts}")
    print(f"  Proxies: {'Enabled' if use_proxies else 'Disabled'}")
    print(f"  Sessions: {'Enabled' if use_sessions else 'Disabled'}")
    print(f"  Rate limit: {rate_limit} requests/minute")
    if len(categories) > 1:
        print(f"  Estimated time: ~{len(categories) * 10} minutes")
    else:
        print(f"  Estimated time: ~10 minutes")
    print("-" * 80)
    print()
    print("Starting scraping process...")
    print("=" * 80)
    print()
    
    try:
        # Create industrial scraper
        scraper = create_industrial_scraper(
            headless=False,  # Set to True for production
            debug=True,
            rate_limit_per_minute=rate_limit,
            use_proxies=use_proxies,
            use_sessions=use_sessions,
            max_concurrent=1
        )
        
        with scraper:
            # Login once for all categories
            print("Logging in to Facebook...")
            if not scraper.login():
                print("\n❌ Login failed. Check credentials in .env file")
                return 1
            
            print("✓ Login successful")
            print()
            
            # Track overall results
            all_results = {}
            start_time = datetime.now()
            
            # Process each category
            for idx, category in enumerate(categories, 1):
                print("=" * 80)
                print(f"CATEGORY {idx}/{len(categories)}: {category.upper()}")
                print("=" * 80)
                print()
                
                try:
                    # Scrape category
                    print(f"Scraping top 10 hashtags for {category}...")
                    print("(This may take a while due to rate limiting and anti-detection measures)")
                    print()
                    
                    results = scraper.get_top_10_trending(category, max_posts)
                    
                    if not results:
                        print(f"⚠️  No results found for {category}")
                        all_results[category] = None
                        print()
                        continue
                    
                    # Display results
                    print()
                    print("-" * 80)
                    print(f"TOP 10 TRENDING HASHTAGS - {category.upper()}")
                    print("-" * 80)
                    print()
                    
                    for i, hashtag in enumerate(results, 1):
                        print(f"{i}. #{hashtag['hashtag']}")
                        print(f"   Trending Score: {hashtag['trending_score']}/100")
                        print(f"   Engagement Score: {hashtag['engagement_score']}/10")
                        print(f"   Posts: {hashtag['post_count']}")
                        print(f"   Avg Engagement: {int(hashtag['avg_engagement']):,}")
                        print(f"   Sentiment: {hashtag['sentiment']} ({hashtag['sentiment_score']:+.2f})")
                        print()
                    
                    # Save results
                    version_id = str(uuid.uuid4())
                    scraper.save_results(results, category, version_id)
                    all_results[category] = results
                    
                    print(f"✓ Category '{category}' completed and saved")
                    print()
                    
                    # Add delay between categories to avoid rate limiting
                    if idx < len(categories):
                        delay = 30  # 30 seconds between categories
                        print(f"⏳ Waiting {delay} seconds before next category (avoiding rate limits)...")
                        import time
                        time.sleep(delay)
                        print()
                    
                except Exception as e:
                    print(f"❌ Error processing category '{category}': {e}")
                    all_results[category] = None
                    import traceback
                    traceback.print_exc()
                    print()
                    continue
            
            # Display overall metrics
            elapsed_time = (datetime.now() - start_time).total_seconds()
            metrics = scraper.get_metrics()
            
            print()
            print("=" * 80)
            print("OVERALL SCRAPING METRICS")
            print("=" * 80)
            print(f"Categories Processed: {len(categories)}")
            print(f"Categories Successful: {sum(1 for r in all_results.values() if r is not None)}")
            print(f"Total Requests: {metrics['total_requests']}")
            print(f"Successful: {metrics['successful_requests']}")
            print(f"Failed: {metrics['failed_requests']}")
            print(f"Success Rate: {metrics['success_rate']:.2f}%")
            print(f"Total Posts Scraped: {metrics['total_posts_scraped']}")
            print(f"Total Hashtags Found: {metrics['total_hashtags_found']}")
            print(f"Avg Response Time: {metrics['avg_response_time']:.2f}s")
            print(f"Total Time: {elapsed_time:.0f}s ({elapsed_time/60:.1f} minutes)")
            
            if 'proxy_stats' in metrics:
                proxy_stats = metrics['proxy_stats']
                print()
                print("Proxy Statistics:")
                print(f"  Total Proxies: {proxy_stats['total_proxies']}")
                print(f"  Healthy Proxies: {proxy_stats['healthy_proxies']}")
                print(f"  Dead Proxies: {proxy_stats['dead_proxies']}")
            
            print()
            print("=" * 80)
            print("✓ All results saved:")
            print(f"  - JSON files in data/ directory (one per category)")
            print(f"  - Supabase database (if configured)")
            print(f"  - Session persisted (if enabled)")
            print("=" * 80)
            
            return 0
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

