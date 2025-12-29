"""Script to verify that all required columns exist in the twitter table."""
import os
import sys
import codecs
from dotenv import load_dotenv
from supabase import create_client, Client

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    exit(1)

print("Connecting to Supabase...")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Connected successfully!\n")
    
    # Required columns
    required_columns = {
        'language': 'TEXT',
        'retweets': 'BIGINT',
        'likes': 'BIGINT',
        'comments': 'BIGINT',
        'reactions': 'BIGINT',
        'first_seen': 'TIMESTAMPTZ',
        'last_seen': 'TIMESTAMPTZ'
    }
    
    print("Checking for required columns...")
    print("=" * 60)
    
    # Try to get table structure by attempting a select with all columns
    try:
        # Try selecting with the new columns
        test_data = {
            "platform": "Twitter",
            "topic_hashtag": "#TestColumnCheck",
            "engagement_score": 0.0,
            "sentiment_polarity": 0.0,
            "sentiment_label": "Neutral",
            "language": "en",
            "posts": 0,
            "views": 0,
            "retweets": 0,
            "likes": 0,
            "metadata": {},
            "version_id": "00000000-0000-0000-0000-000000000000",
            "first_seen": "2024-01-01T00:00:00Z",
            "last_seen": "2024-01-01T00:00:00Z"
        }
        
        # Try insert to see which columns are missing
        try:
            result = supabase.table('twitter').insert(test_data).execute()
            print("SUCCESS: All columns exist! The table is ready.")
            # Clean up test record
            supabase.table('twitter').delete().eq('topic_hashtag', '#TestColumnCheck').execute()
            print("\nNext step: Run the scraper!")
            exit(0)
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: {error_msg}\n")
            
            # Check which specific column is missing
            missing = []
            for col in required_columns.keys():
                if col in error_msg.lower():
                    missing.append(col)
                    print(f"  MISSING: {col} ({required_columns[col]})")
            
            if missing:
                print(f"\n{'='*60}")
                print(f"ACTION REQUIRED: Add {len(missing)} missing column(s)")
                print("="*60)
                print("\nRun this SQL in Supabase SQL Editor:\n")
                print("-- Add missing columns")
                for col in missing:
                    col_type = required_columns[col]
                    if col_type == 'BIGINT':
                        print(f"ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS {col} {col_type} DEFAULT 0;")
                    else:
                        print(f"ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS {col} {col_type};")
                
                print("\n-- Set defaults")
                if 'retweets' in missing or 'likes' in missing:
                    print("UPDATE public.twitter SET retweets = 0 WHERE retweets IS NULL;")
                    print("UPDATE public.twitter SET likes = 0 WHERE likes IS NULL;")
                if 'language' in missing:
                    print("UPDATE public.twitter SET language = 'unknown' WHERE language IS NULL;")
                
                print("\n-- Refresh schema cache (important!)")
                print("NOTIFY pgrst, 'reload schema';")
                
    except Exception as e:
        print(f"ERROR checking columns: {e}")
        
except Exception as e:
    print(f"ERROR: Connection failed: {e}")

