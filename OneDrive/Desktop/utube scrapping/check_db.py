import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config
from supabase import create_client

cfg = get_config()
client = create_client(cfg.supabase_url, cfg.supabase_anon_key)

# Query recent records
result = client.table('youtube').select('id, topic_hashtag, engagement_score, sentiment_label, scraped_at, metadata').order('scraped_at', desc=True).limit(5).execute()

print(f"Total records: {len(result.data)}")
print("\nRecent records:")
for i, r in enumerate(result.data, 1):
    lang = r.get('metadata', {}).get('language', 'N/A') if isinstance(r.get('metadata'), dict) else 'N/A'
    print(f"{i}. {r.get('topic_hashtag')} | Score: {r.get('engagement_score')} | Lang: {lang} | {r.get('scraped_at')}")
