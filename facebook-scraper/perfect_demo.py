#!/usr/bin/env python3
"""
Perfect Scraper Demo
====================

Demonstrates the perfect Facebook scraper with enhanced accuracy and reliability.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from perfect_scraper import create_perfect_scraper

def main():
    print("=" * 80)
    print("Perfect Facebook Scraper Demo")
    print("=" * 80)
    print()
    print("Features:")
    print("  ✓ Advanced error handling and retry logic")
    print("  ✓ Smart hashtag extraction and filtering")
    print("  ✓ Enhanced engagement metrics calculation")
    print("  ✓ Sophisticated trending score algorithm")
    print("  ✓ Data validation and quality checks")
    print("  ✓ Rate limiting and throttling")
    print()
    
    # Available categories
    valid_categories = ['technology', 'business', 'health', 'food', 'travel', 'fashion', 'entertainment', 'sports']
    
    # Configuration
    print("Available categories:")
    for i, cat in enumerate(valid_categories, 1):
        print(f"  {i}. {cat}")
    print()
    
    category_input = input("Enter category name or number (default: technology): ").strip().lower()
    
    # Handle number input
    if category_input.isdigit():
        cat_num = int(category_input)
        if 1 <= cat_num <= len(valid_categories):
            category = valid_categories[cat_num - 1]
        else:
            print(f"Invalid number. Using 'technology' as default.")
            category = "technology"
    elif category_input in valid_categories:
        category = category_input
    elif not category_input or category_input == ".":
        print("Using 'technology' as default.")
        category = "technology"
    else:
        print(f"Invalid category '{category_input}'. Using 'technology' as default.")
        category = "technology"
    
    max_posts_input = input("Max posts to scrape (default 100): ").strip()
    max_posts = int(max_posts_input) if max_posts_input.isdigit() else 100
    
    print()
    print(f"Category: {category}")
    print(f"Max posts: {max_posts}")
    print("-" * 80)
    print()
    
    try:
        # Create perfect scraper
        scraper = create_perfect_scraper(debug=False)
        
        # Check if cookies are available
        if not scraper.cookies_available:
            print("⚠️  WARNING: No cookies file found!")
            print()
            print("Facebook requires cookies to access most content.")
            print("Without cookies, the scraper will likely find 0 posts.")
            print()
            print("Options:")
            print("  1. Export cookies (recommended):")
            print("     - Install browser extension: Get cookies.txt LOCALLY")
            print("     - Go to facebook.com and log in")
            print("     - Export cookies as cookies.txt")
            print("     - Set FACEBOOK_COOKIES_FILE=cookies.txt in .env")
            print()
            print("  2. Use Playwright scraper instead (already has login):")
            print("     - Run: python industrial_demo.py")
            print("     - It handles login automatically")
            print()
            continue_choice = input("Continue anyway? (y/n, default: y): ").strip().lower()
            if continue_choice == 'n':
                print("Exiting. Please set up cookies or use industrial_demo.py")
                return 1
            print()
        
        # Get trending hashtags
        print(f"Scraping trending hashtags for {category}...")
        print("(This may take a few minutes for perfect accuracy)")
        print()
        
        results = scraper.get_trending_hashtags(category, max_posts=max_posts)
        
        if not results:
            print("❌ No results found")
            print()
            if not scraper.cookies_available:
                print("⚠️  This is likely because no cookies are configured.")
                print()
                print("Facebook requires authentication to access content.")
                print("Without cookies, most pages return empty results.")
                print()
                print("Solutions:")
                print("  1. Export cookies (see HOW_TO_USE_COOKIES.md)")
                print("  2. Use Playwright scraper: python industrial_demo.py")
            else:
                print("Tips:")
                print("  - Try a different category")
                print("  - Increase max_posts")
                print("  - Check your cookies file is valid")
            return 1
        
        # Display results
        print()
        print("=" * 80)
        print(f"TOP 10 TRENDING HASHTAGS - {category.upper()}")
        print("=" * 80)
        print()
        
        for i, hashtag in enumerate(results, 1):
            print(f"{i}. #{hashtag['hashtag']}")
            print(f"   Trending Score: {hashtag['trending_score']:.1f}/100")
            print(f"   Engagement Score: {hashtag['engagement_score']:.1f}/10")
            print(f"   Posts: {hashtag['post_count']}")
            print(f"   Total Engagement: {int(hashtag['total_engagement']):,}")
            print(f"   Avg Engagement: {int(hashtag['avg_engagement']):,}")
            print(f"   Metrics: {int(hashtag['avg_likes']):,} likes, "
                  f"{int(hashtag['avg_comments']):,} comments, "
                  f"{int(hashtag['avg_shares']):,} shares")
            print(f"   Sentiment: {hashtag['sentiment']} ({hashtag['sentiment_score']:+.2f})")
            print()
        
        # Save results
        filepath = scraper.save_results(results, category)
        
        # Display stats
        stats = scraper.get_stats()
        print("=" * 80)
        print("SCRAPING STATISTICS")
        print("=" * 80)
        print(f"Total Posts Scraped: {stats['total_posts_scraped']}")
        print(f"Total Hashtags Found: {stats['total_hashtags_found']}")
        print(f"Successful Requests: {stats['successful_requests']}")
        print(f"Failed Requests: {stats['failed_requests']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Duration: {stats['duration_seconds']:.1f} seconds")
        print()
        print(f"✓ Results saved to: {filepath}")
        print("=" * 80)
        
        return 0
        
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("\nInstall with:")
        print("  pip install facebook-scraper")
        print("  pip install textblob")
        return 1
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

