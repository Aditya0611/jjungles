import zipfile
import os

def zip_project(output_filename):
    source_dir = os.getcwd()
    # Files/folders to exclude
    excludes = {
        '.venv', '__pycache__', '.git', '.env', 'out', 'dist', 
        '.vscode', 'create_zip.py', output_filename, '.pytest_cache',
        'hashtags.db', 'youtube_scraper.log'
    }
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in excludes]
            
            for file in files:
                if file in excludes or file.endswith('.zip') or file.endswith('.pyc') or file.endswith('.log'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                
                print(f"Adding: {arcname}")
                zipf.write(file_path, arcname)
                
    print(f"\nSuccessfully created {output_filename}")

if __name__ == "__main__":
    zip_project("youtube_scraper_sprint1_checklist_completed.zip")
