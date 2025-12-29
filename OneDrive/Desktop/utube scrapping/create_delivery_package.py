"""
Create a professional delivery package for the YouTube Scraper project.
Includes all essential files and excludes development artifacts.
"""
import os
import zipfile
from datetime import datetime

def create_delivery_package():
    # Get current timestamp for unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"youtube_scraper_delivery_{timestamp}.zip"
    
    # Define what to include
    include_patterns = [
        # Core application files
        "main.py",
        "requirements.txt",
        
        # Source code
        "src/*.py",
        
        # Odoo integration
        "odoo_addons/**/*.py",
        "odoo_addons/**/*.xml",
        "odoo_addons/**/__manifest__.py",
        
        # Documentation
        "README.md",
        "DATABASE_SETUP.md",
        "SPRINT1_FINAL_SUMMARY.md",
        "DB_VERIFICATION_PROOF.md",
        "DB_STORAGE_VERIFIED.md",
        
        # Configuration examples
        ".env.example",
        
        # Database setup
        "supabase_setup.sql",
        
        # Test files
        "tests/check_config.py",
        "tests/test_proxy_enforcement.py",
        "tests/test_db_integration.py",
        
        # Verification scripts
        "verify_db_storage.py",
        "check_db.py",
    ]
    
    # Directories to exclude completely
    exclude_dirs = {
        ".venv", "venv", "env", "__pycache__", ".pytest_cache",
        ".git", ".github", "dist", "build", "*.egg-info",
        "out", "logs"
    }
    
    # Files to exclude
    exclude_files = {
        ".env",  # Never include actual credentials
        "youtube_scraper.log",
        ".gitignore",
        "create_zip.py",
        "create_delivery_package.py",
        "fix_table_refs.py",
    }
    
    # Exclude old zip files
    exclude_extensions = {".zip", ".pyc", ".pyo", ".pyd", ".db"}
    
    print("="*70)
    print("CREATING CLIENT DELIVERY PACKAGE")
    print("="*70)
    print(f"\nPackage name: {zip_filename}")
    print("\nIncluding:")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        files_added = 0
        
        for root, dirs, files in os.walk('.'):
            # Remove excluded directories from traversal
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            
            # Get relative path
            rel_root = os.path.relpath(root, '.')
            if rel_root == '.':
                rel_root = ''
            
            for file in files:
                # Skip excluded files
                if file in exclude_files:
                    continue
                
                # Skip excluded extensions
                if any(file.endswith(ext) for ext in exclude_extensions):
                    continue
                
                # Get full path
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, '.')
                
                # Add to zip
                zipf.write(file_path, rel_path)
                files_added += 1
                
                # Print progress for important files
                if any(pattern in rel_path for pattern in ['src/', 'odoo_addons/', 'main.py', '.md', 'requirements.txt']):
                    print(f"  ✓ {rel_path}")
        
        print(f"\n✅ Total files added: {files_added}")
    
    # Get file size
    size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    
    print("="*70)
    print("PACKAGE CREATED SUCCESSFULLY!")
    print("="*70)
    print(f"\n📦 File: {zip_filename}")
    print(f"📊 Size: {size_mb:.2f} MB")
    print(f"📁 Files: {files_added}")
    
    print("\n✅ Ready for client delivery!")
    print("\nPackage includes:")
    print("  • Complete source code (src/)")
    print("  • Odoo integration (odoo_addons/)")
    print("  • All documentation")
    print("  • Database verification proof")
    print("  • Test scripts")
    print("  • Configuration examples")
    
    print("\n⚠️  Excluded (as expected):")
    print("  • .env file (credentials)")
    print("  • Virtual environment")
    print("  • Log files")
    print("  • Cache files")
    print("  • Old zip files")
    
    return zip_filename

if __name__ == "__main__":
    create_delivery_package()
