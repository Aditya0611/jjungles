import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from twitter_scraper_app.utils import logger

class RetryQueue:
    """Manages a local SQLite queue for failed Supabase writes."""
    def __init__(self, db_path: str = "failed_writes.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payload TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        attempts INTEGER DEFAULT 0
                    )
                """)
        except Exception as e:
            logger.error(f"Failed to initialize local sqlite queue: {e}")

    def add(self, record: Dict[str, Any]):
        """Add a record to the retry queue."""
        try:
            payload = json.dumps(record)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO queue (payload) VALUES (?)", (payload,))
            logger.info(f"Added record to local retry queue (total in queue might be more)")
        except Exception as e:
            logger.error(f"Failed to add record to local queue: {e}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all records from the queue with their IDs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id, payload FROM queue")
                return [{"id": row[0], "data": json.loads(row[1])} for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to retrieve from local queue: {e}")
            return []

    def remove(self, record_id: int):
        """Remove a record from the queue by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM queue WHERE id = ?", (record_id,))
        except Exception as e:
            logger.error(f"Failed to remove from local queue: {e}")

    def clear(self):
        """Clear all records from the queue."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM queue")
        except Exception as e:
            logger.error(f"Failed to clear local queue: {e}")

    def count(self) -> int:
        """Count remaining records in the queue."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM queue")
                return cursor.fetchone()[0]
        except Exception:
            return 0

# Global instance
retry_queue = RetryQueue()
