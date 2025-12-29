import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Supabase credentials not found.")
    sys.exit(1)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Check for the latest entry in the twitter table
    result = supabase.table('twitter').select('scraped_at').order('scraped_at', desc=True).limit(1).execute()
    
    if result.data:
        last_scrape = result.data[0]['scraped_at']
        print(f"Latest Data Heartbeat: {last_scrape}")
    else:
        print("No data found in 'twitter' table.")
except Exception as e:
    print(f"Error checking database: {e}")
