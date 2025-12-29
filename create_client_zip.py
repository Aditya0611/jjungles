"""
Create client delivery zip package with essential files only
Excludes runtime-generated files and demo artifacts
"""

import os
import shutil
import zipfile
from pathlib import Path

# Essential files to include
ESSENTIAL_FILES = [
    'linkedin_hashtag_scraper_playwright.py',
    'requirements.txt',
    'setup_playwright.py',
    'db/unified_trends_schema.sql',  # New unified schema
    'db/linkedin_table_schema.sql',  # Keep for backward compatibility reference
    'README.md',
    '.env.example',
    'proxies.txt',
    '.github/workflows/run_scraper.yml',
    'stub_scrapers.py',            # REQUIRED: imported by platform_manager
    'verify_setup.py',              # HELPER: useful for client validation
    # Core modules
    'logger.py',
    'qa_dashboard.html',
    'base_scraper.py',
    'tests/test_linkedin_scraper_smoke.py',
    'db/supabase_schema.sql',  # Full schema with all fields
    # Cross Platform Modules
    'config.py',
    'platform_manager.py',
    'scrape_all_platforms.py',
    # Documentation
    'docs/CROSS_PLATFORM_README.md',
    'docs/PRODUCTION_READINESS.md',
    'docs/SUPABASE_SETUP.md',
    'docs/TROUBLESHOOT_SUPABASE.md',
    'docs/LINKEDIN_API_OPTIONS.md',
    'docs/SUPABASE_SETUP_INSTRUCTIONS.md',
    'docs/VIEWS_EXPLANATION.md',
    # Utility modules
    'utils/__init__.py',
    'utils/proxies.py',
    'utils/analysis.py',
    # Odoo Integration
    'odoo_linkedin_scraper/__init__.py',
    'odoo_linkedin_scraper/__manifest__.py',
    'odoo_linkedin_scraper/models/__init__.py',
    'odoo_linkedin_scraper/models/linkedin_scraper.py',
    'odoo_linkedin_scraper/models/res_config_settings.py',
    'odoo_linkedin_scraper/data/ir_cron_data.xml',
    'odoo_linkedin_scraper/views/linkedin_scraper_views.xml',
    'odoo_linkedin_scraper/views/res_config_settings_views.xml',
    'odoo_linkedin_scraper/security/ir.model.access.csv',
]

# Files to EXCLUDE (runtime-generated outputs and demo artifacts)
EXCLUDED_FILES = [
    'scraper_logs.jsonl',      # Runtime log output
    'dashboard_data.js',        # Generated dashboard data
    'trending_hashtags.json',   # Runtime scrape results
    'trending_hashtags_*.json', # Any platform-specific results
    '*.zip',                    # Previous zip packages
]

def is_excluded(filename):
    """Check if a file should be excluded from the zip"""
    import fnmatch
    for pattern in EXCLUDED_FILES:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False

def create_client_zip():
    """Create zip package with essential files only, excluding runtime-generated files"""
    
    zip_filename = 'linkedin-scraper-client.zip'
    
    # Remove existing zip if it exists
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
        print(f"Removed existing {zip_filename}")
    
    print("\n" + "=" * 70)
    print("Creating Client Delivery Package")
    print("=" * 70)
    
    included_files = []
    missing_files = []
    excluded_found = []
    
    # Check for excluded files that exist (for reporting)
    for pattern in EXCLUDED_FILES:
        if '*' in pattern:
            # Handle wildcard patterns
            import glob
            matches = glob.glob(pattern)
            excluded_found.extend(matches)
        elif os.path.exists(pattern):
            excluded_found.append(pattern)
    
    # Create zip file
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in ESSENTIAL_FILES:
            # Validate file is not in excluded list
            if is_excluded(file_path):
                print(f"WARNING: {file_path} is in ESSENTIAL_FILES but matches EXCLUDED pattern!")
                continue
                
            if os.path.exists(file_path):
                # Preserve directory structure for files in subdirectories
                if '/' in file_path or '\\' in file_path:
                    zipf.write(file_path, file_path)
                else:
                    zipf.write(file_path, os.path.basename(file_path))
                included_files.append(file_path)
                print(f"[+] Added: {file_path}")
            else:
                missing_files.append(file_path)
                print(f"[-] Missing: {file_path}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("Package Summary")
    print("=" * 70)
    
    print(f"\n[OK] Included Files ({len(included_files)}):")
    for file in included_files:
        print(f"   * {file}")
    
    if missing_files:
        print(f"\n[!] Missing Files ({len(missing_files)}):")
        for file in missing_files:
            print(f"   * {file}")
    
    if excluded_found:
        print(f"\n[X] Excluded Files (not in zip) ({len(excluded_found)}):")
        for file in excluded_found:
            print(f"   * {file} - Runtime-generated, not shipped to client")
    
    # Get file size
    file_size = os.path.getsize(zip_filename) / (1024 * 1024)  # MB
    print(f"\n[*] Package: {zip_filename}")
    print(f"[*] Size: {file_size:.2f} MB")
    print(f"[*] Status: Ready for client delivery!")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    create_client_zip()

