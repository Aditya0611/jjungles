from odoo import http
from odoo.http import request

class TrendController(http.Controller):

    @http.route('/jj_trend/fetch', type='json', auth='user')
    def fetch_trends(self, platform=None, date_from=None, date_to=None,
                     min_engagement=None, hashtag=None, limit=200):
        service = request.env["jj.trend.service"].sudo()
        data = service.fetch_trends(
            platform=platform,
            date_from=date_from,
            date_to=date_to,
            min_engagement=min_engagement,
            hashtag=hashtag,
            limit=limit,
        )
        return {"trends": data}

    @http.route('/jj_trend/fetch_top_per_platform', type='json', auth='user')
    def fetch_top_per_platform(self, top_n=1, platform=None, date_from=None, date_to=None,
                             min_engagement=None, hashtag=None):
        """Fetch top N hashtags from each platform separately with filters"""
        service = request.env["jj.trend.service"].sudo()
        data = service.fetch_top_per_platform(
            top_n=top_n,
            platform=platform,
            date_from=date_from,
            date_to=date_to,
            min_engagement=min_engagement,
            hashtag=hashtag
        )
        return {"trends": data}

