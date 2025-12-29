import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Verification")

def verify_unified_writes():
    """Verify that Instagram data is being written correctly to the unified trends table."""
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Error: SUPABASE_URL or SUPABASE_KEY missing in .env")
        return

    supabase = create_client(url, key)
    
    print("\n--- UNIFIED DB WRITE VERIFICATION ---")
    
    try:
        # Check 'trends' table for Instagram records
        print("Checking 'trends' table...")
        result = supabase.table('trends').select('platform, topic_hashtag, engagement_score, created_at').eq('platform', 'Instagram').order('created_at', desc=True).limit(5).execute()
        
        if result.data:
            print(f"✅ SUCCESS: Found {len(result.data)} recent records in 'trends' table.")
            for i, record in enumerate(result.data):
                hashtag = record.get('topic_hashtag', 'N/A')
                score = record.get('engagement_score', 0)
                ts = record.get('created_at', 'N/A')
                print(f"   [{i+1}] Hashtag: {hashtag:15} | Score: {score:.2f} | Time: {ts}")
        else:
            print("⚠️ WARNING: No Instagram records found in 'trends' table yet.")
        
    except Exception as e:
        print(f"❌ Verification Error: {e}")
        
    print("\n--- End Verification ---\n")

if __name__ == "__main__":
    verify_unified_writes()
