import os
from dotenv import load_dotenv
from supabase import create_client, Client

def check_logging_tables():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    tables = [
        'instagram', 'trends', 'hashtags', 'trend_hashtags', 
        'engagement_metrics', 'snapshots', 'scraper_runs', 
        'scraper_logs', 'scraper_config'
    ]
    
    with open("table_check_results.txt", "w") as f:
        f.write("--- TABLE STATUS SUMMARY ---\n")
        for table in tables:
            try:
                supabase.table(table).select('count', count='exact').limit(0).execute()
                status = "EXISTS"
            except Exception:
                status = "MISSING"
            f.write(f"{table:20}: {status}\n")
    print("Results written to table_check_results.txt")

if __name__ == "__main__":
    check_logging_tables()
