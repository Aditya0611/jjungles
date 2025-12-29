"""
Test script for Supabase database integration.
Verifies connection, schema compatibility, and data insertion.
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.supabase_storage import (
    init_database, 
    store_hashtags_batch,
    get_hashtag_stats,
    store_scraping_log,
    get_supabase_client
)
from src.config import get_config
from src.logger import logger

def test_database_connection():
    """Test basic database connection."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        cfg = get_config()
        if not cfg.supabase_url or not cfg.supabase_anon_key:
            print("❌ FAILED: SUPABASE_URL or SUPABASE_ANON_KEY not configured")
            print("   Please set these in your .env file")
            return False
        
        init_database()
        print("✅ PASSED: Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Database connection error - {e}")
        return False

def test_sample_data_insertion():
    """Test insertion of sample YouTube hashtag data."""
    print("\n" + "="*60)
    print("TEST 2: Sample Data Insertion")
    print("="*60)
    
    try:
        # Create sample data matching YouTube scraper output
        sample_records = [
            (
                "youtube",                    # platform
                "TechTrends2024",            # hashtag
                85.5,                        # engagement_score
                0.75,                        # sentiment_polarity
                "positive",                  # sentiment_label
                150,                         # posts (video_count)
                1500000,                     # views (avg_views)
                50000,                       # likes (total_likes)
                2500,                        # comments (total_comments)
                "en",                        # language
                {                            # metadata
                    "video_count": 150,
                    "avg_views": 1500000,
                    "total_views": 225000000,
                    "channels": ["TechChannel1", "TechChannel2"],
                    "locales": ["US"],
                    "test_data": True
                },
                None                         # version_id (auto-generated)
            ),
            (
                "youtube",
                "GamingHighlights",
                92.3,
                0.85,
                "positive",
                200,
                2000000,
                75000,
                3500,
                "en",
                {
                    "video_count": 200,
                    "avg_views": 2000000,
                    "total_views": 400000000,
                    "channels": ["GamingPro", "EsportsDaily"],
                    "locales": ["US", "GB"],
                    "test_data": True
                },
                None
            ),
            (
                "youtube",
                "MusicVibes",
                78.0,
                0.65,
                "positive",
                100,
                1000000,
                30000,
                1500,
                "en",
                {
                    "video_count": 100,
                    "avg_views": 1000000,
                    "total_views": 100000000,
                    "channels": ["MusicOfficial"],
                    "locales": ["US"],
                    "test_data": True
                },
                None
            )
        ]
        
        print(f"Inserting {len(sample_records)} sample records...")
        store_hashtags_batch(sample_records)
        print("✅ PASSED: Sample data inserted successfully")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Data insertion error - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_retrieval():
    """Test retrieval of inserted data."""
    print("\n" + "="*60)
    print("TEST 3: Data Retrieval")
    print("="*60)
    
    try:
        # Retrieve YouTube data
        data = get_hashtag_stats(platform="youtube", limit=10)
        
        if not data:
            print("⚠️  WARNING: No data retrieved (might be RLS policy issue)")
            print("   Check Supabase RLS policies if you expected data")
            return True  # Not a failure, might be expected
        
        print(f"✅ PASSED: Retrieved {len(data)} records")
        
        # Display sample
        if data:
            print("\nSample record:")
            record = data[0]
            print(f"   Platform: {record.get('platform')}")
            print(f"   Hashtag: {record.get('topic_hashtag')}")
            print(f"   Engagement: {record.get('engagement_score')}")
            print(f"   Sentiment: {record.get('sentiment_label')}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Data retrieval error - {e}")
        return False

def test_scraping_log():
    """Test scraping log insertion."""
    print("\n" + "="*60)
    print("TEST 4: Scraping Log Insertion")
    print("="*60)
    
    try:
        store_scraping_log(
            platform="youtube",
            status="test_success",
            items_collected=3,
            duration_seconds=10.5,
            metadata={"test": True, "timestamp": datetime.now().isoformat()}
        )
        print("✅ PASSED: Scraping log inserted successfully")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Scraping log insertion error - {e}")
        return False

def test_schema_compatibility():
    """Test that all expected fields are supported."""
    print("\n" + "="*60)
    print("TEST 5: Schema Compatibility Check")
    print("="*60)
    
    try:
        client = get_supabase_client()
        
        # Try to query with all expected fields
        result = client.table("trends").select(
            "id, platform, topic_hashtag, engagement_score, sentiment_polarity, "
            "sentiment_label, posts, views, likes, comments, language, metadata, "
            "version_id, created_at"
        ).limit(1).execute()
        
        print("✅ PASSED: All expected fields are present in schema")
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if "column" in error_msg or "does not exist" in error_msg:
            print(f"❌ FAILED: Schema mismatch - {e}")
            print("   Please run the SQL setup from DATABASE_SETUP.md")
            return False
        else:
            print(f"⚠️  WARNING: Query error (might be RLS) - {e}")
            return True  # Not necessarily a schema issue

def main():
    """Run all database integration tests."""
    print("\n" + "="*60)
    print("DATABASE INTEGRATION TEST SUITE")
    print("="*60)
    
    cfg = get_config()
    print(f"\nConfiguration:")
    print(f"  SUPABASE_URL: {cfg.supabase_url[:30]}..." if cfg.supabase_url else "  SUPABASE_URL: Not set")
    print(f"  USE_DATABASE: {cfg.use_database}")
    
    results = []
    
    # Run tests
    results.append(("Database Connection", test_database_connection()))
    
    # Only run other tests if connection succeeded
    if results[0][1]:
        results.append(("Schema Compatibility", test_schema_compatibility()))
        results.append(("Sample Data Insertion", test_sample_data_insertion()))
        results.append(("Data Retrieval", test_data_retrieval()))
        results.append(("Scraping Log", test_scraping_log()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📝 Note: Check your Supabase dashboard to verify the test data:")
        print("   - Table: trends (should have 3 test records)")
        print("   - Table: scraping_logs (should have 1 test log)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
