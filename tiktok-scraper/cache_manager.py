"""
Local Cache Manager for Supabase Data

This module provides a local SQLite cache for trend data to:
1. Reduce Supabase queries (read cache)
2. Handle offline data collection (write cache)
3. Sync offline data when connection is restored
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DB_PATH = os.environ.get("CACHE_DB_PATH", "local_cache.db")

class LocalCache:
    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Table for caching trend data (read cache)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trend_cache (
                    topic TEXT,
                    platform TEXT,
                    data JSON,
                    cached_at TIMESTAMP,
                    PRIMARY KEY (topic, platform)
                )
            """)
            
            # Table for offline uploads (write cache)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT,
                    data JSON,
                    created_at TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize local cache: {e}")

    def get_trend_data(self, topic: str, platform: str = "TikTok") -> Optional[Dict[str, Any]]:
        """Get cached trend data if not expired (e.g., < 1 hour old)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT data, cached_at FROM trend_cache WHERE topic = ? AND platform = ?", 
                (topic, platform)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                data_json, cached_at_str = row
                # Check expiration (1 hour)
                cached_at = datetime.fromisoformat(cached_at_str)
                age = (datetime.now() - cached_at).total_seconds()
                
                if age < 3600: # 1 hour
                    return json.loads(data_json)
                else:
                    logger.debug(f"Cache expired for {topic}")
            
            return None
        except Exception as e:
            logger.error(f"Failed to read from local cache: {e}")
            return None

    def set_trend_data(self, topic: str, data: Dict[str, Any], platform: str = "TikTok"):
        """Cache trend data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO trend_cache (topic, platform, data, cached_at)
                VALUES (?, ?, ?, ?)
                """,
                (topic, platform, json.dumps(data), datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to write to local cache: {e}")

    def queue_offline_upload(self, table_name: str, data: List[Dict[str, Any]]):
        """Queue data for offline upload."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO offline_queue (table_name, data, created_at) VALUES (?, ?, ?)",
                (table_name, json.dumps(data), datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Queued {len(data)} records for offline upload to {table_name}")
        except Exception as e:
            logger.error(f"Failed to queue offline upload: {e}")

    def fetch_offline_queue(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch items from offline queue."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM offline_queue ORDER BY created_at ASC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            
            items = []
            for row in rows:
                items.append({
                    "id": row["id"],
                    "table_name": row["table_name"],
                    "data": json.loads(row["data"]),
                    "created_at": row["created_at"]
                })
            
            conn.close()
            return items
        except Exception as e:
            logger.error(f"Failed to fetch offline queue: {e}")
            return []

    def remove_offline_item(self, item_id: int):
        """Remove item from offline queue after successful upload."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM offline_queue WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to remove offline item {item_id}: {e}")
