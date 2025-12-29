import os
import zipfile
from datetime import datetime
from pathlib import Path

def create_project_zip():
    """Create a clean zip of the Instagram scraper project."""
    
    # Get project root (parent of the scripts folder)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    zip_filename = f"instagram_scraper_{timestamp}.zip"
    zip_path = project_root / zip_filename
    
    # Files to explicitly include
    include_files = [
        'proxies.txt',
        'proxies.txt.example',
        'migrations/FINAL_DB_SETUP.sql',
        'README.md',
        'HOW_TO_RUN.md',
        'CLIENT_DELIVERY_INSTRUCTIONS.md',
        'requirements.txt'
    ]
    
    # Files and directories to exclude
    exclude_patterns = {
        '.coverage',
        '.env',
        '.env.example',
        'vrnv', 
        'venv',
        'node_modules',
        '*.zip',
        '.git',
        '.github',
        '.pytest_cache',
        '__pycache__',
        'tests',                 # Exclude tests
        'scripts/verify_db_writes.py', # Exclude internal verification tool
        'db_verification_proof.txt',   # Exclude proof file
        'table_check_results.txt',
        'instagram_scraper.log',
        '*.pyc',
        '*.pyo',
        '*.log',
        '*.png',
        'instance',
        'pytest.ini'
    }
    
    def should_exclude(path_str):
        """Check if a path should be excluded."""
        path = Path(path_str)
        
        # Check each part of the path
        parts = list(path.parts)
        for part in parts:
            if part in exclude_patterns:
                return True
            # Check wildcard patterns
            if part.endswith('.pyc') or part.endswith('.pyo') or part.endswith('.log') or part.endswith('.png') or part.endswith('.zip'):
                return True
        
        return False
    
    print(f"📦 Creating project zip: {zip_filename}")
    print("=" * 60)
    
    file_count = 0
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files
        for root, dirs, files in os.walk(project_root):
            # Convert root to relative path for exclusion check
            rel_root = Path(root).relative_to(project_root)
            
            # Filter out excluded directories in-place to stop os.walk from descending
            dirs[:] = [d for d in dirs if not should_exclude(str(rel_root / d))]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(project_root)
                
                # Skip the zip file itself
                if file == zip_filename:
                    continue
                
                # Check if it should be excluded
                is_excluded = should_exclude(str(rel_path))
                
                # Check if it should be explicitly included
                is_included = str(rel_path) in include_files
                
                if is_excluded and not is_included:
                    continue
                
                # Add to zip
                zipf.write(file_path, rel_path)
                file_count += 1
                
                if file_count % 20 == 0:
                    print(f"  ✅ Added {file_count} files...")
    
    # Get zip size
    zip_size = zip_path.stat().st_size / (1024 * 1024)  # MB
    
    print("=" * 60)
    print(f"🚀 [SUCCESS] Zip created successfully!")
    print(f"   📂 File: {zip_filename}")
    print(f"   📊 Size: {zip_size:.2f} MB")
    print(f"   📝 Files: {file_count}")
    print("=" * 60)
    
    return str(zip_path)

if __name__ == "__main__":
    create_project_zip()
