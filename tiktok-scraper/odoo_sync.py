#!/usr/bin/env python3
"""
Odoo Sync Module
Syncs data from Supabase to Odoo via XMLRPC.
"""

import os
import xmlrpc.client
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Odoo Configuration
ODOO_URL = os.environ.get("ODOO_URL")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_USERNAME = os.environ.get("ODOO_USERNAME")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD")

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

class OdooSync:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.uid: Optional[int] = None
        self.models: Optional[xmlrpc.client.ServerProxy] = None
        self.common: Optional[xmlrpc.client.ServerProxy] = None
        
        self._init_supabase()
        self._init_odoo()

    def _init_supabase(self):
        """Initialize Supabase client."""
        try:
            if SUPABASE_URL and SUPABASE_KEY:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase client initialized")
            else:
                logger.warning("Supabase credentials missing")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")

    def _init_odoo(self):
        """Initialize Odoo XMLRPC connection."""
        try:
            if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
                logger.warning("Odoo credentials missing")
                return

            self.common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
            try:
                self.uid = self.common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
            except Exception as auth_error:
                # Log without password
                logger.error(f"Odoo authentication failed: {str(auth_error)}")
                return
            
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
                logger.info(f"Connected to Odoo (UID: {self.uid})")
            else:
                logger.error("Odoo authentication failed")
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {e}")

    def sync_trends(self, limit: int = 100):
        """Sync top trends from Supabase to Odoo."""
        if not self.supabase or not self.models or not self.uid:
            logger.warning("Sync skipped: Missing connections")
            return

        try:
            # Fetch recent trends from Supabase
            # Get latest snapshot version to ensure we sync fresh data
            today = datetime.now(timezone.utc).date().isoformat()
            
            response = self.supabase.table("tiktok")\
                .select("*")\
                .order("scraped_at", desc=True)\
                .limit(limit)\
                .execute()
            
            trends = response.data
            if not trends:
                logger.info("No trends found to sync")
                return

            synced_count = 0
            for trend in trends:
                try:
                    if self._sync_single_trend(trend):
                        synced_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync trend {trend.get('topic')}: {e}")

            logger.info(f"Synced {synced_count}/{len(trends)} trends to Odoo")

        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def _sync_single_trend(self, trend: Dict[str, Any]) -> bool:
        """Sync a single trend record to Odoo."""
        # Map Supabase fields to Odoo model fields
        # Assuming Odoo model 'social.media.trend' exists
        # You may need to adjust the model name and fields based on your Odoo setup
        
        odoo_model = 'social.media.trend'
        
        # Check if trend already exists in Odoo (deduplication)
        # Using topic and date/hour as unique key
        domain = [
            ('name', '=', trend.get('topic')),
            ('platform', '=', 'tiktok'),
            # Add more domain criteria if needed to avoid duplicates within same day
        ]
        
        existing_ids = self.models.execute_kw(
            ODOO_DB, self.uid, ODOO_PASSWORD,
            odoo_model, 'search',
            [domain],
            {'limit': 1}
        )

        vals = {
            'name': trend.get('topic'),
            'platform': 'tiktok',
            'score': trend.get('engagement_score'),
            'posts_count': trend.get('posts'), # Ensure type compatibility
            'views_count': trend.get('views'),
            'sentiment_score': trend.get('sentiment_polarity'),
            'sentiment_label': trend.get('sentiment_label'),
            'scraped_at': trend.get('scraped_at'),
            'url': trend.get('metadata', {}).get('source_url'),
            # Add other fields as needed
        }

        if existing_ids:
            # Update existing record
            self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                odoo_model, 'write',
                [existing_ids, vals]
            )
            logger.debug(f"Updated Odoo record for {trend.get('topic')}")
        else:
            # Create new record
            self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                odoo_model, 'create',
                [vals]
            )
            logger.debug(f"Created Odoo record for {trend.get('topic')}")
            
        return True

if __name__ == "__main__":
    # Test run
    syncer = OdooSync()
    syncer.sync_trends()
