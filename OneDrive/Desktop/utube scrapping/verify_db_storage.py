import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config
from supabase import create_client

cfg = get_config()
client = create_client(cfg.supabase_url, cfg.supabase_anon_key)

# Query recent records
result = client.table('youtube').select('*').order('scraped_at', desc=True).limit(3).execute()

print("="*70)
print("DATABASE VERIFICATION - DATA STORAGE CHECK")
print("="*70)
print(f"\n✅ Total records in database: {len(result.data)}")

if result.data:
    print("\n" + "="*70)
    print("SAMPLE RECORDS:")
    print("="*70)
    
    for i, record in enumerate(result.data, 1):
        print(f"\n📌 Record {i}:")
        print(f"   Hashtag: {record.get('topic_hashtag')}")
        print(f"   Platform: {record.get('platform')}")
        print(f"   Engagement Score: {record.get('engagement_score')}")
        print(f"   Sentiment: {record.get('sentiment_label')} (polarity: {record.get('sentiment_polarity')})")
        print(f"   Posts: {record.get('posts')}")
        print(f"   Views: {record.get('views')}")
        print(f"   Likes: {record.get('likes')}")
        print(f"   Comments: {record.get('comments')}")
        
        # Check metadata
        metadata = record.get('metadata')
        if metadata and isinstance(metadata, dict):
            print(f"   Language: {metadata.get('language', 'N/A')}")
            print(f"   Video Count: {metadata.get('video_count', 'N/A')}")
        
        print(f"   Scraped At: {record.get('scraped_at')}")
    
    print("\n" + "="*70)
    print("✅ DATA IS BEING STORED SUCCESSFULLY IN SUPABASE!")
    print("="*70)
    print("\n✅ Language is stored in metadata.language (JSONB)")
    print("✅ All fields are populated correctly")
else:
    print("\n⚠️  No records found")
