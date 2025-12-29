"""Quick script to test Supabase connection and verify table structure."""
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
    print("Connected successfully!")
    
    # Check if table exists and get structure
    print("\nChecking table structure...")
    try:
        # Try to select one record to verify table exists
        result = supabase.table('twitter').select('*').limit(1).execute()
        print(f"Table 'twitter' exists and is accessible")
        print(f"Current record count: Checking...")
        
        # Count records
        count_result = supabase.table('twitter').select('id', count='exact').execute()
        record_count = count_result.count if hasattr(count_result, 'count') else len(result.data)
        print(f"Total records in table: {record_count}")
        
        # Show sample record structure if any exist
        if result.data and len(result.data) > 0:
            print("\nSample record structure:")
            sample = result.data[0]
            for key, value in sample.items():
                print(f"   - {key}: {type(value).__name__} = {value}")
        else:
            print("\nWARNING: No records found in table")
            print("   This could mean:")
            print("   1. The scraper hasn't run yet")
            print("   2. Data was cleared")
            print("   3. RLS policies are blocking reads")
        
        # Check for required columns
        print("\nChecking for required columns...")
        required_columns = ['platform', 'topic_hashtag', 'engagement_score', 'posts', 'retweets', 'likes']
        if result.data and len(result.data) > 0:
            sample = result.data[0]
            missing = [col for col in required_columns if col not in sample]
            if missing:
                print(f"WARNING: Missing columns: {', '.join(missing)}")
                print("   Run the migration script: database_migration_add_engagement.sql")
            else:
                print("All required columns present")
        else:
            print("WARNING: Cannot verify columns (no records to inspect)")
            print("   Make sure your table has these columns:")
            for col in required_columns:
                print(f"   - {col}")
        
    except Exception as e:
        print(f"ERROR: Error accessing table: {e}")
        print("\nPossible issues:")
        print("1. Table 'twitter' doesn't exist - create it using the SQL in INSTALLATION_GUIDE.txt")
        print("2. RLS (Row Level Security) policies are blocking access")
        print("3. Table name is different (check your Supabase dashboard)")
    
    # Test insert (will be rolled back if there's an issue)
    print("\nTesting insert capability...")
    try:
        test_data = {
            "platform": "Twitter",
            "topic_hashtag": "#TestConnection",
            "engagement_score": 5.0,
            "sentiment_polarity": 0.0,
            "sentiment_label": "Neutral",
            "language": "en",
            "posts": 0,
            "views": 0,
            "retweets": 0,
            "likes": 0,
            "metadata": {"test": True}
        }
        
        # Try to insert
        insert_result = supabase.table('twitter').insert(test_data).execute()
        
        if insert_result.data:
            print("Insert test successful!")
            # Clean up test record
            supabase.table('twitter').delete().eq('topic_hashtag', '#TestConnection').execute()
            print("Test record cleaned up")
        else:
            print("WARNING: Insert returned no data (might be RLS blocking)")
            
    except Exception as e:
        print(f"ERROR: Insert test failed: {e}")
        print("\nPossible issues:")
        print("1. Missing columns (retweets, likes) - run migration script")
        print("2. RLS policies blocking inserts")
        print("3. Data type mismatches")
        print("4. Required fields not provided")
    
except Exception as e:
    print(f"ERROR: Connection failed: {e}")
    print("\nCheck:")
    print("1. SUPABASE_URL is correct in .env file")
    print("2. SUPABASE_KEY is correct in .env file")
    print("3. Your Supabase project is active")
    print("4. Internet connection is working")

