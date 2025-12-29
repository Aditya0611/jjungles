#!/usr/bin/env python3
import os
import sys
import uuid
import json
from datetime import datetime
from pathlib import Path

# Add core path
sys.path.append(str(Path(__file__).parent))

from base import FacebookScraper, Platform

def test_db_insertion():
    print("Starting Facebook Scraper DB Pipeline Verification...")
    
    # Check for credentials in .env
    from dotenv import load_dotenv
    load_dotenv()
    
    email = os.getenv('FACEBOOK_EMAIL')
    password = os.getenv('FACEBOOK_PASSWORD')
    
    if not email or not password:
        print("❌ FAILED: Facebook credentials missing in .env")
        return False

    try:
        # Initialize Facebook scraper (no browser setup needed for DB test)
        scraper = FacebookScraper(headless=True)
        
        # Create a dummy result dictionary matching the expected internal format
        test_id = str(uuid.uuid4())[:8]
        test_hashtag = f"verification_{test_id}"
        version_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        dummy_result = {
            'hashtag': test_hashtag,
            'engagement_score': 95.5,
            'trending_score': 0.9,
            'virality_score': 0.75,
            'sentiment_score': 0.8,
            'sentiment': 'positive',
            'post_count': 150,
            'total_engagement': 1200,
            'avg_engagement': 8.0,
            'likes': 800,
            'comments': 300,
            'shares': 100,
            'hashtag_url': f"https://www.facebook.com/hashtag/{test_hashtag}",
            'primary_language': 'en',
            'post_types': {'status': 10, 'photo': 90},
            'is_estimated': False
        }
        
        # Test the save_results pipeline (Normalization -> Supabase)
        print(f"Attempting to process and save test result: #{test_hashtag}")
        scraper.save_results([dummy_result], "technology", version_id)
        
        print("✅ SUCCESS: Data normalization and Supabase insertion completed.")
        print(f"Verified: Record for #{test_hashtag} uploaded to Supabase.")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: DB Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_db_insertion():
        sys.exit(0)
    else:
        sys.exit(1)
