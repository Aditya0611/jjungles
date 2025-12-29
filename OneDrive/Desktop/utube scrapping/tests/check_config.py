"""Quick diagnostic script to check environment configuration."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config

cfg = get_config()

print("="*60)
print("ENVIRONMENT CONFIGURATION CHECK")
print("="*60)
print(f"\nSUPABASE_URL: {cfg.supabase_url[:40] + '...' if cfg.supabase_url else 'NOT SET'}")
print(f"SUPABASE_ANON_KEY: {cfg.supabase_anon_key[:40] + '...' if cfg.supabase_anon_key else 'NOT SET'}")
print(f"USE_DATABASE: {cfg.use_database}")
print(f"PROXY_LIST: {cfg.proxy_list[:50] + '...' if cfg.proxy_list else 'NOT SET'}")
print(f"PROXY_STRICT_MODE: {cfg.proxy_strict_mode}")
print(f"YOUTUBE_API_KEY: {cfg.youtube_api_key[:20] + '...' if cfg.youtube_api_key else 'NOT SET'}")

print("\n" + "="*60)

if not cfg.supabase_url:
    print("❌ SUPABASE_URL is not set in .env file")
    sys.exit(1)

if not cfg.supabase_anon_key:
    print("❌ SUPABASE_ANON_KEY is not set in .env file")
    sys.exit(1)

print("✅ All required credentials are configured")

# Try to connect
print("\nTesting Supabase connection...")
try:
    from src.supabase_storage import init_database
    init_database()
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
