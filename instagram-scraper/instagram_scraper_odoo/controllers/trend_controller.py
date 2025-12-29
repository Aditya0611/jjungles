from odoo import http
from odoo.http import request
import json

class TrendController(http.Controller):
    @http.route('/instagram/trends', type='json', auth='user')
    def get_trends(self, platform=None, category=None, limit=10):
        """API endpoint to fetch filtered trends for the dashboard widget."""
        domain = []
        if platform:
            domain.append(('platform', '=', platform))
        if category:
            domain.append(('category', '=', category))
        
        trends = request.env['instagram.trend'].search(domain, limit=limit)
        return [{
            'id': t.id,
            'platform': t.platform,
            'hashtag': t.hashtag,
            'likes': t.likes,
            'comments': t.comments,
            'views': t.views,
            'engagement_score': t.engagement_score,
            'scraped_at': t.scraped_at.isoformat() if t.scraped_at else None,
            'category': t.category,
            'language': t.language
        } for t in trends]
