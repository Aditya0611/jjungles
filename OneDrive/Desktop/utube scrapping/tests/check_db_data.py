"""
Quick script to check if data is being stored in Supabase database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config
from supabase import create_client

def check_database():
    print("\n" + "="*60)
    print("DATABASE VERIFICATION CHECK")
    print("="*60)
    
    try:
        cfg = get_config()
        client = create_client(cfg.supabase_url, cfg.supabase_anon_key)
        
        # Query recent records
        result = client.table('youtube').select('*').order('scraped_at', desc=True).limit(10).execute()
        
        print(f"\n✅ Database connection successful!")
        print(f"📊 Total records found: {len(result.data)}")
        
        if result.data:
            print("\n" + "="*60)
            print("RECENT RECORDS:")
            print("="*60)
            
            for i, record in enumerate(result.data[:5], 1):
                print(f"\nRecord {i}:")
                print(f"  Hashtag: {record.get('topic_hashtag')}")
                print(f"  Platform: {record.get('platform')}")
                print(f"  Engagement Score: {record.get('engagement_score')}")
                print(f"  Sentiment: {record.get('sentiment_label')} ({record.get('sentiment_polarity')})")
                print(f"  Posts: {record.get('posts')}")
                print(f"  Views: {record.get('views')}")
                print(f"  Likes: {record.get('likes')}")
                print(f"  Comments: {record.get('comments')}")
                
                # Check if language is in metadata
                metadata = record.get('metadata', {})
                if isinstance(metadata, dict):
                    print(f"  Language (in metadata): {metadata.get('language', 'N/A')}")
                    print(f"  Video Count: {metadata.get('video_count', 'N/A')}")
                
                print(f"  Scraped At: {record.get('scraped_at')}")
            
            print("\n" + "="*60)
            print("✅ DATA IS BEING STORED SUCCESSFULLY!")
            print("="*60)
        else:
            print("\n⚠️  No records found in database.")
            print("   This could mean:")
            print("   1. No scraping has been run yet")
            print("   2. Data insertion is failing")
            print("   3. RLS policies are blocking reads")
            
    except Exception as e:
        print(f"\n❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
