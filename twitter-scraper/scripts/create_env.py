"""
Quick script to create .env file with Supabase credentials.
Usage: python create_env.py <SUPABASE_URL> <SUPABASE_KEY>
Or set environment variables: SUPABASE_URL and SUPABASE_KEY
"""

import os
import sys

def create_env_file(url=None, key=None):
    """Create .env file with Supabase credentials."""
    env_path = ".env"
    
    # Get credentials from command line args or environment variables
    if not url:
        url = os.getenv("SUPABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not key:
        key = os.getenv("SUPABASE_KEY") or (sys.argv[2] if len(sys.argv) > 2 else None)
    
    # If still no credentials, prompt
    if not url:
        url = input("Enter Supabase Project URL: ").strip()
    if not key:
        key = input("Enter Supabase anon public key: ").strip()
    
    if not url or not key:
        print("Error: Both SUPABASE_URL and SUPABASE_KEY are required.")
        print("\nUsage:")
        print("  python create_env.py <URL> <KEY>")
        print("  Or set environment variables: SUPABASE_URL and SUPABASE_KEY")
        return False
    
    # Validate URL format
    if not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url
    
    # Create .env file content
    env_content = f"""# Supabase Configuration
SUPABASE_URL={url}
SUPABASE_KEY={key}
"""
    
    # Check if .env already exists
    if os.path.exists(env_path):
        response = input(f"\n.env file already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled. Existing .env file preserved.")
            return False
    
    # Write to file
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"\nSuccessfully created .env file!")
        print(f"Location: {os.path.abspath(env_path)}")
        print("\nYou can now run: python t3_scraper.py")
        return True
    except Exception as e:
        print(f"Error creating .env file: {e}")
        return False

if __name__ == "__main__":
    create_env_file()

