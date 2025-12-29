# Odoo Scheduler Integration

This scraper is designed to be triggered by an Odoo Cron job.

## Integration Steps

1.  **Script Location**: Ensure the `src` folder and `main.py` are accessible to the Odoo server (or executed via Docker/Subprocess).
2.  **Cron Job Definition**:
    Create an Odoo Scheduled Action (technical settings -> automation -> scheduled actions) with the following python code:

```python
import subprocess
import os

# Path to the scraper project
scraper_path = "/path/to/utube_scrapping"
python_exec = "/usr/bin/python3" # Or your venv python

# Run the scraper
# Flags: --locales US,IN --categories gaming --limit 50
result = subprocess.run(
    [python_exec, "main.py", "--locales", "US", "--categories", "gaming"], 
    cwd=scraper_path, 
    capture_output=True, 
    text=True
)

if result.returncode != 0:
    raise Exception(f"Scraper Failed:\n{result.stderr}")
```

## Parameter Passing
You can dynamically pass parameters from Odoo models if you build a custom module wrapper.

## Database
The scraper writes directly to Supabase (`trends` table). Odoo can read from this table using `psycopg2` or via a Foreign Data Wrapper (FDW) to display metrics inside Odoo views.
