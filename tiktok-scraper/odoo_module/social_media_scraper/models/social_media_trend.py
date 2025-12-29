# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SocialMediaTrend(models.Model):
    _name = 'social.media.trend'
    _description = 'Social Media Trending Topic'
    _order = 'score desc, scraped_at desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Topic/Hashtag',
        required=True,
        index=True
    )
    
    platform = fields.Selection([
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
    ], string='Platform', required=True, index=True)
    
    score = fields.Float(
        string='Engagement Score',
        help='Engagement/virality score (0.0-10.0)'
    )
    
    posts_count = fields.Integer(string='Posts')
    views_count = fields.Integer(string='Views')
    
    sentiment_score = fields.Float(
        string='Sentiment',
        help='Sentiment polarity (-1.0 to 1.0)'
    )
    
    sentiment_label = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], string='Sentiment Label')
    
    scraped_at = fields.Datetime(
        string='Scraped At',
        required=True,
        index=True
    )
    
    url = fields.Char(string='Source URL')
    
    metadata = fields.Json(string='Metadata')
    
    is_hot = fields.Boolean(
        string='Hot Right Now',
        compute='_compute_is_hot',
        store=True,
        help='Trending in the last 6 hours with high engagement'
    )
    
    color = fields.Integer(
        string='Color',
        compute='_compute_color'
    )
    
    @api.depends('scraped_at', 'score')
    def _compute_is_hot(self):
        """Determine if trend is hot (recent + high engagement)."""
        from datetime import datetime, timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=6)
        
        for record in self:
            record.is_hot = (
                record.scraped_at >= cutoff and
                record.score >= 7.0
            )
    
    @api.depends('score')
    def _compute_color(self):
        """Color code based on engagement score."""
        for record in self:
            if record.score >= 8.0:
                record.color = 10  # Red (hot)
            elif record.score >= 6.0:
                record.color = 3   # Orange (warm)
            elif record.score >= 4.0:
                record.color = 4   # Yellow (moderate)
            else:
                record.color = 0   # Default (cool)
    
    @api.model
    def get_whats_hot(self, limit=10, platform=False, days=1, min_score=6.0):
        """Get current hot trends for dashboard widget."""
        from datetime import datetime, timedelta
        
        # Default to 6 hours if close to 0, otherwise use days
        if days <= 0.25:
            cutoff = fields.Datetime.now() - timedelta(hours=6)
        else:
            cutoff = fields.Datetime.now() - timedelta(days=days)
        
        domain = [
            ('scraped_at', '>=', cutoff),
            ('score', '>=', min_score)
        ]
        
        if platform:
            domain.append(('platform', '=', platform))
            
        trends = self.search(domain, order='score desc', limit=limit)
        
        return [{
            'id': t.id,
            'name': t.name,
            'platform': t.platform,
            'score': t.score,
            'posts_count': t.posts_count,
            'views_count': t.views_count,
            'sentiment_label': t.sentiment_label,
        } for t in trends]
