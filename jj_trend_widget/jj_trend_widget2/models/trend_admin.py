from odoo import models, fields

class TrendAdminLine(models.TransientModel):
    _name = "jj.trend.admin.line"
    _description = "Raw Trend Data (Transient)"

    platform = fields.Char()
    timestamp = fields.Datetime()
    title = fields.Char()
    engagement_score = fields.Float()
    url = fields.Char()
    industry = fields.Char()
