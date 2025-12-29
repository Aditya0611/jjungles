#!/usr/bin/env python3
"""
Automated Facebook Scraper - For CI/CD
=======================================
Non-interactive version for GitHub Actions
Runs all categories automatically without prompts
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from industrial_scraper import IndustrialFacebookScraper, create_industrial_scraper

def load_categories():
    """Load all categories from config file"""
    # Try multiple path resolution strategies
    script_dir = Path(__file__).parent.absolute()
    working_dir = Path.cwd()
    
    # List of potential config paths to try
    potential_paths = [
        script_dir / "config" / "categories.json",  # Relative to script
        working_dir / "config" / "categories.json",  # Relative to working directory
        Path("config") / "categories.json",  # Relative to current directory
        script_dir.parent / "config" / "categories.json",  # One level up (in case script is in subdirectory)
    ]
    
    config_path = None
    
    # Debug information
    print(f"Script directory: {script_dir}")
    print(f"Working directory: {working_dir}")
    print(f"Searching for config/categories.json...")
    
    # Try each potential path
    for path in potential_paths:
        abs_path = path.absolute()
        if abs_path.exists() and abs_path.is_file():
            config_path = abs_path
            print(f"✓ Found config file at: {config_path}")
            break
        else:
            print(f"  - Not found: {abs_path}")
    
    # If not found, list directory contents to help debug
    if not config_path:
        print(f"\n❌ Config file not found in any expected location")
        print(f"\nScript directory contents:")
        try:
            for item in sorted(script_dir.iterdir()):
                print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
        except Exception as e:
            print(f"  Error listing directory: {e}")
        
        print(f"\nWorking directory contents:")
        try:
            for item in sorted(working_dir.iterdir()):
                print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
        except Exception as e:
            print(f"  Error listing directory: {e}")
        
        # Check if config directory exists anywhere
        config_dirs = []
        for base_dir in [script_dir, working_dir]:
            config_dir = base_dir / "config"
            if config_dir.exists():
                config_dirs.append(config_dir)
                print(f"\nFound config directory at: {config_dir}")
                print(f"Contents of {config_dir}:")
                try:
                    for item in sorted(config_dir.iterdir()):
                        print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
                except Exception as e:
                    print(f"  Error listing directory: {e}")
        
        if not config_dirs:
            print(f"\n❌ Config directory not found anywhere")
        
        return []
    
    # config_path is already confirmed to exist, so proceed with reading it
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
        
        if not categories_data:
            print(f"⚠ Config file is empty: {config_path}")
            return []
        
        return list(categories_data.keys())
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from {config_path}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error reading config file {config_path}: {e}")
        return []

def main():
    """Run automated scraping for ALL categories (non-interactive)"""
    
    print("=" * 80)
    print("Automated Facebook Scraper - GitHub Actions")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load all categories
    all_categories = load_categories()
    if not all_categories:
        print("❌ No categories found in config/categories.json")
        return 1
    
    print(f"Found {len(all_categories)} categories: {', '.join(all_categories)}")
    print()
    
    # Configuration - STRICT ENFORCEMENT
    categories = all_categories
    max_posts = int(os.getenv('MAX_POSTS', '100'))
    use_proxies = True # MANDATORY
    use_sessions = True
    rate_limit = int(os.getenv('RATE_LIMIT', '30'))
    headless = os.getenv('HEADLESS', 'true').lower() == 'true'
    
    print("Configuration (STRICT ENFORCEMENT):")
    print(f"  Categories: {len(categories)} ({', '.join(categories)})")
    print(f"  Max posts per category: {max_posts}")
    print(f"  Proxies: ENFORCED")
    print(f"  Sessions: {'Enabled' if use_sessions else 'Disabled'}")
    print(f"  Rate limit: {rate_limit} requests/minute")
    print(f"  Headless: {headless}")
    print(f"  Estimated time: ~{len(categories) * 10} minutes")
    print("-" * 80)
    print()
    print("Starting scraping process...")
    print("=" * 80)
    print()
    
    try:
        # Create industrial scraper
        scraper = create_industrial_scraper(
            headless=headless,
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
                print("\n❌ Login failed. Check credentials in environment variables")
                return 1
            
            print("✓ Login successful")
            print()
            
            # Track overall results
            all_results = {}
            start_time = datetime.now()
            successful_categories = 0
            failed_categories = 0
            
            # Process each category
            for idx, category in enumerate(categories, 1):
                print("=" * 80)
                print(f"CATEGORY {idx}/{len(categories)}: {category.upper()}")
                print("=" * 80)
                print()
                
                try:
                    # Scrape category
                    print(f"Scraping top 10 hashtags for {category}...")
                    print(f"Search terms: {', '.join(scraper.categories.get(category.lower(), {}).get('keywords', []))[:5]}")
                    print()
                    results = scraper.scrape_category_hashtags(
                        category=category,
                        max_posts=max_posts
                    )
                    
                    if results and len(results) > 0:
                        all_results[category] = results
                        successful_categories += 1
                        print(f"✓ Category '{category}' completed: {len(results)} hashtags found")
                        
                        # MANDATORY: Save to Supabase immediately after each category
                        print(f"📤 Uploading results for {category} to Supabase...")
                        try:
                            # Use current timestamp for version_id to group this run's results
                            run_id = f"run_{start_time.strftime('%Y%m%d_%H%M%S')}"
                            scraper.save_results(results, category, run_id)
                            print(f"✓ Results for {category} persisted to Supabase")
                        except Exception as e:
                            print(f"❌ CRITICAL: Supabase insertion failed for {category}: {e}")
                            print("Exiting to ensure data integrity.")
                            raise e 
                        
                        print()
                        print("Top Hashtags Found:")
                        print("-" * 80)
                        # Display top 10 hashtags with details
                        for idx, hashtag in enumerate(results[:10], 1):
                            print(f"\n{idx}. #{hashtag.get('hashtag', 'N/A')}")
                            print(f"   Engagement Score: {hashtag.get('engagement_score', 0):.2f}")
                            print(f"   Trending Score: {hashtag.get('trending_score', 0):.2f}")
                            print(f"   Posts: {hashtag.get('post_count', 0)}")
                            print(f"   Total Engagement: {hashtag.get('total_engagement', 0):,}")
                            print(f"   Avg Engagement: {hashtag.get('avg_engagement', 0):.1f}")
                            print(f"   Likes: {hashtag.get('likes', 0):,} | Comments: {hashtag.get('comments', 0):,} | Shares: {hashtag.get('shares', 0):,}")
                            print(f"   Sentiment: {hashtag.get('sentiment', 'neutral')} ({hashtag.get('sentiment_score', 0):.2f})")
                            if hashtag.get('primary_language'):
                                print(f"   Language: {hashtag.get('primary_language', 'en')}")
                            if hashtag.get('hashtag_url'):
                                print(f"   URL: {hashtag.get('hashtag_url', '')}")
                        print()
                    else:
                        failed_categories += 1
                        print(f"⚠ Category '{category}' completed but no results found")
                    
                    # Delay between categories to avoid rate limiting
                    if idx < len(categories):
                        print(f"\nWaiting 30 seconds before next category...")
                        import time
                        time.sleep(30)
                    
                except Exception as e:
                    failed_categories += 1
                    print(f"❌ Error scraping category '{category}': {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Final summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print()
            print("=" * 80)
            print("SCRAPING SESSION COMPLETE")
            print("=" * 80)
            print(f"Total Categories: {len(categories)}")
            print(f"Successful: {successful_categories}")
            print(f"Failed: {failed_categories}")
            print(f"Total Duration: {duration/60:.1f} minutes")
            print()
            
            # Display summary of all results
            if all_results:
                print("=" * 80)
                print("SCRAPED RESULTS SUMMARY")
                print("=" * 80)
                total_hashtags = sum(len(results) for results in all_results.values())
                print(f"Total Hashtags Scraped: {total_hashtags}")
                print()
                
                for category, results in all_results.items():
                    print(f"\n📊 {category.upper()} ({len(results)} hashtags):")
                    print("-" * 80)
                    for idx, hashtag in enumerate(results[:5], 1):  # Show top 5 per category
                        tag = hashtag.get('hashtag', 'N/A')
                        engagement = hashtag.get('engagement_score', 0)
                        posts = hashtag.get('post_count', 0)
                        print(f"  {idx}. #{tag} | Engagement: {engagement:.2f} | Posts: {posts}")
                print()
            
            # Display metrics
            metrics = scraper.get_metrics()
            print("=" * 80)
            print("FINAL METRICS")
            print("=" * 80)
            print(f"  Total Requests: {metrics.get('total_requests', 0)}")
            print(f"  Successful: {metrics.get('successful_requests', 0)}")
            print(f"  Failed: {metrics.get('failed_requests', 0)}")
            print(f"  Success Rate: {metrics.get('success_rate', 0.0):.2f}%")
            print(f"  Total Posts Scraped: {metrics.get('total_posts_scraped', 0)}")
            print(f"  Total Hashtags Found: {metrics.get('total_hashtags_found', 0)}")
            print(f"  Avg Response Time: {metrics.get('avg_response_time', 0.0):.2f}s")
            print()
            
            return 0 if failed_categories == 0 else 1
            
    except KeyboardInterrupt:
        print("\n\n⚠ Scraping interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

