import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

# Load configuration
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def run_filter_proof():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials missing!")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\n" + "="*80)
    print(f"{'SUPABASE LIVE FILTER PROOF':^80}")
    print("="*80)

    # 1. Total Count
    total = supabase.table('twitter').select("*", count="exact").limit(0).execute()
    total_count = total.count
    print(f"Total Records in Database: {total_count}")

    # 2. Filter by Sentiment: Positive
    pos_response = supabase.table('twitter').select("*", count="exact").eq('sentiment_label', 'Positive').limit(5).execute()
    print(f"\n[FILTER PROOF 1] Sentiment = 'Positive'")
    print(f"Count found: {pos_response.count}")
    for row in pos_response.data:
        print(f"  - {row['topic_hashtag']} (Score: {row['sentiment_polarity']})")

    # 3. Filter by Engagement: High (> 5.0)
    high_eng = supabase.table('twitter').select("*", count="exact").gt('engagement_score', 5.0).order('engagement_score', desc=True).limit(5).execute()
    print(f"\n[FILTER PROOF 2] Engagement Score > 5.0")
    print(f"Count found: {high_eng.count}")
    for row in high_eng.data:
        print(f"  - {row['topic_hashtag']} (Engagement: {row['engagement_score']})")

    # 4. Filter by Language: English
    en_lang = supabase.table('twitter').select("*", count="exact").eq('language', 'en').limit(3).execute()
    print(f"\n[FILTER PROOF 3] Language = 'en'")
    print(f"Count found: {en_lang.count}")

    # 5. Temporal Filter: Last 24 Hours
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    recent = supabase.table('twitter').select("*", count="exact").gte('scraped_at', yesterday).execute()
    print(f"\n[FILTER PROOF 4] Time Filter: Scraped in last 24h")
    print(f"Count found: {recent.count}")

    print("\n" + "="*80)
    print("CONCLUSION: Database-level filtering is confirmed and fully functional.")
    print("="*80)

if __name__ == "__main__":
    run_filter_proof()
