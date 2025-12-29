import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Supabase credentials not found. Cannot check remote logs.")
    sys.exit(1)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    result = supabase.table('scraping_logs').select('*').order('start_time', desc=True).limit(1).execute()
    
    if result.data:
        log = result.data[0]
        print(f"Latest Scrape Log Status:")
        print(f"  ID: {log['id']}")
        print(f"  Scraper: {log['scraper_name']}")
        print(f"  Status: {log['status']}")
        print(f"  Started: {log['start_time']}")
        print(f"  Ended: {log.get('end_time', 'N/A')}")
        
        if log['status'] == 'running':
            print("\n>>> THE SCRAPER IS CURRENTLY MARKED AS RUNNING <<<")
        else:
            print("\n>>> THE SCRAPER IS NOT CURRENTLY RUNNING <<<")
    else:
        print("No scraping logs found.")
except Exception as e:
    print(f"Error checking logs: {e}")
