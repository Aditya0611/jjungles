import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load configuration
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_proof():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials missing!")
        return

    print(f"Connecting to: {SUPABASE_URL}")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("\n--- DATABASE PROOF: RECENT INSERTIONS ---")
    try:
        # Query last 10 records
        response = supabase.table('twitter').select(
            "topic_hashtag, engagement_score, sentiment_label, scraped_at"
        ).order('scraped_at', desc=True).limit(10).execute()

        data = response.data
        if not data:
            print("No data found in 'twitter' table.")
            return

        # Print header
        print(f"{'HASHTAG':<30} | {'ENGAGEMENT':<12} | {'SNTMNT':<10} | {'SCRAPED AT (UTC)'}")
        print("-" * 80)

        for row in data:
            hashtag = row.get('topic_hashtag', 'N/A')
            engagement = row.get('engagement_score', 0.0)
            sentiment = row.get('sentiment_label', 'Neutral')
            scraped_at = row.get('scraped_at', 'N/A')
            
            # Format display
            print(f"{hashtag[:28]:<30} | {engagement:<12} | {sentiment:<10} | {scraped_at}")

        print("-" * 80)
        print(f"SUCCESS: Found {len(data)} recent records in your database.")
        print(f"Current System Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    except Exception as e:
        print(f"FAILED to fetch proof: {e}")

if __name__ == "__main__":
    get_proof()
