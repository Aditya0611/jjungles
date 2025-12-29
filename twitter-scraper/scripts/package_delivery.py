import os
import zipfile
import datetime

def create_delivery_zip():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    zip_filename = f"Twitter_Scraper_Delivery_Final_Professionalized.zip"
    zip_path = os.path.join(project_root, zip_filename)

    inclusions = [
        "twitter_scraper_app",
        "odoo_addon",
        "scripts",
        "tests",
        "README.md",
        "INSTALLATION_GUIDE.txt",
        "ENGAGEMENT_METRICS_EXTRACTION.md",
        "ENGAGEMENT_SCORE_EXPLANATION.md",
        "LANGUAGE_DETECTION_SETUP.md",
        "TREND_RECORD_SCHEMA.md",
        "TROUBLESHOOTING_SUPABASE.md",
        "requirements.txt",
        ".env.example",
        "schema_and_sample.sql",
        "t3_scraper.py"
    ]

    exclusions = [
        ".git",
        ".github",
        ".env",
        ".zip",
        "failed_writes.db",
        "__pycache__",
        ".pytest_cache",
        "package_delivery.py"  # Exclude itself
    ]

    print(f"Creating delivery zip: {zip_filename}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in inclusions:
            item_path = os.path.join(project_root, item)
            if not os.path.exists(item_path):
                print(f"Warning: {item} not found, skipping.")
                continue

            if os.path.isfile(item_path):
                zipf.write(item_path, item)
                print(f"Added file: {item}")
            elif os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    # Filter directories
                    dirs[:] = [d for d in dirs if not any(ex in d for ex in exclusions)]
                    
                    for file in files:
                        if any(ex in file for ex in exclusions):
                            continue
                        
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, project_root)
                        zipf.write(file_path, rel_path)
                print(f"Added directory: {item}")

    print(f"\nSuccess! Delivery package created at: {zip_path}")
    return zip_path

if __name__ == "__main__":
    create_delivery_zip()
