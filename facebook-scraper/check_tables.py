from supabase import create_client
import os
from dotenv import load_dotenv

def check_tables():
    load_dotenv()
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    if not url or not key:
        print("Missing Supabase credentials")
        return
        
    s = create_client(url, key)
    tables = ['facebook', 'scrape_runs', 'scraping_log']
    
    with open('table_results_clean.txt', 'w', encoding='utf-8') as out:
        out.write(f"Checking tables at {url}...\n")
        print(f"Checking tables at {url}...")
        for t in tables:
            try:
                r = s.table(t).select('*', count='exact').limit(1).execute()
                line = f"RESULT|{t}|FOUND|{r.count}\n"
                out.write(line)
                print(line.strip())
            except Exception as e:
                msg = str(e).lower()
                status = "NOT_FOUND" if ("does not exist" in msg or "not found" in msg) else "ERROR"
                line = f"RESULT|{t}|{status}|{str(e)[:100]}\n"
                out.write(line)
                print(line.strip())

if __name__ == "__main__":
    check_tables()
