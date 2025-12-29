
import os
import time
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
from uuid import uuid4

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")  # Use anon key for client-side ops, or service_role if available
TRENDS_TABLE = os.getenv("SUPABASE_TRENDS_TABLE", "linkedin")

def verify_db_insert():
    print(f"Connecting to Supabase at {SUPABASE_URL}...")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env")
        return False

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Create a test record matching User's schema (NO language/caption columns)
    test_id = str(uuid4())
    test_record = {
        "platform": "test_verification",
        "topic_hashtag": "schema_test_v2",
        "engagement_score": 99.9,
        "sentiment_polarity": 0.5,
        "sentiment_label": "positive",
        # "language": "en",  <-- REMOVED (not in user schema)
        # "caption": "...",  <-- REMOVED (not in user schema)
        "posts": 1,
        "metadata": {
            "test": True,
            "language": "en",        # Testing storage in metadata
            "caption": "test caption" # Testing storage in metadata
        },
        "version_id": test_id
    }
    
    print(f"Attempting to insert test record into '{TRENDS_TABLE}'...")
    try:
        response = supabase.table(TRENDS_TABLE).insert(test_record).execute()
        
        if hasattr(response, 'data') and response.data:
            print("✅ Insert successful!")
            inserted_data = response.data[0]
            metadata = inserted_data.get('metadata', {})
            
            # Verify fields
            print("\nVerifying fields in metadata:")
            print(f"   language (in metadata): {metadata.get('language')} (Expected: 'en')")
            print(f"   caption (in metadata): {metadata.get('caption')} (Expected: 'test caption')")
            
            if metadata.get('language') == 'en':
                print("✅ Schema verification PASSED: Data preserved in JSONB.")
            else:
                print("❌ Schema verification FAILED: Metadata missing fields.")
            
            # Cleanup
            print("\nCleaning up test record...")
            supabase.table(TRENDS_TABLE).delete().eq("version_id", test_id).execute()
            print("✅ Cleanup complete.")
            return True
            
        else:
            print("❌ Insert failed: No data returned.")
            print(response)
            return False
            
    except Exception as e:
        print(f"❌ Error during insertion: {e}")
        return False

if __name__ == "__main__":
    verify_db_insert()
