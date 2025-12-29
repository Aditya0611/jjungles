from odoo import models, fields, api
import os
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

class InstagramTrend(models.Model):
    _name = 'instagram.trend'
    _description = 'Instagram Trending Hashtag'
    _order = 'engagement_score desc'

    platform = fields.Char(string='Platform', required=True)
    hashtag = fields.Char(string='Hashtag', required=True)
    url = fields.Char(string='URL')
    likes = fields.Integer(string='Likes')
    comments = fields.Integer(string='Comments')
    shares = fields.Integer(string='Shares/Saves')
    views = fields.Integer(string='Views')
    engagement_score = fields.Float(string='Engagement Score')
    scraped_at = fields.Datetime(string='Scraped At')
    category = fields.Char(string='Category')
    language = fields.Char(string='Language')

    @api.model
    def sync_from_supabase(self):
        """Fetch latest trends from Supabase and update Odoo."""
        if not SUPABASE_AVAILABLE:
            return
        
        # Expect env vars or config
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            return

        supabase = create_client(url, key)
        
        # Fetch last 50 records ordered by scraped_at
        try:
             response = supabase.table('trends').select("*").order('scraped_at', desc=True).limit(50).execute()
             data = response.data
        except Exception as e:
             _logger.error(f"Supabase sync error: {e}")
             return

        if not data:
            return

        for record in data:
            # Check duplicates
            domain = [
                ('hashtag', '=', record.get('topic_hashtag')),
                ('platform', '=', record.get('platform', 'Instagram')),
                ('scraped_at', '=', record.get('scraped_at'))
            ]
            existing = self.search(domain, limit=1)
            
            vals = {
                'platform': record.get('platform', 'Instagram'),
                'hashtag': record.get('topic_hashtag'),
                'url': record.get('url'),
                'likes': record.get('likes', 0) if record.get('likes') is not None else 0,
                'comments': record.get('comments', 0) if record.get('comments') is not None else 0,
                'shares': record.get('shares', 0) if record.get('shares') is not None else 0,
                'views': record.get('views', 0) if record.get('views') is not None else 0,
                'engagement_score': record.get('engagement_score', 0.0),
                'scraped_at': record.get('scraped_at'),
                'category': record.get('category'),
                'language': record.get('language'),
            }
            
            if not existing:
                self.create(vals)
            else:
                existing.write(vals)

    @api.model
    def run_cron_sync(self):
        self.sync_from_supabase()
