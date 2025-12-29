# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.models import TransientModel

class ResConfigSettings(TransientModel):
    _inherit = 'res.config.settings'

    youtube_scraper_interval_number = fields.Integer(
        string="Interval Number",
        config_parameter='youtube_scraper.interval_number',
        default=1
    )
    youtube_scraper_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string="Interval Unit", config_parameter='youtube_scraper.interval_type', default='days')

    youtube_scraper_active = fields.Boolean(
        string="Active",
        default=True
    )
    youtube_scraper_next_run = fields.Datetime(
        string="Next Execution"
    )

    youtube_scraper_path = fields.Char(
        string="Scraper Project Path",
        config_parameter='youtube_scraper.path',
        help="Absolute path to the youtube scraper directory"
    )
    youtube_python_executable = fields.Char(
        string="Python Executable",
        config_parameter='youtube_scraper.python_executable',
        default="python3",
        help="Path to python executable (e.g., /usr/bin/python3 or path to venv)"
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        # Update the cron job dynamically
        cron = self.env.ref('youtube_scraper_scheduler.ir_cron_youtube_scraper_action', raise_if_not_found=False)
        if cron:
            vals = {
                'interval_number': self.youtube_scraper_interval_number,
                'interval_type': self.youtube_scraper_interval_type,
                'active': self.youtube_scraper_active,
            }
            if self.youtube_scraper_next_run:
                vals['nextcall'] = self.youtube_scraper_next_run
            cron.write(vals)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        cron = self.env.ref('youtube_scraper_scheduler.ir_cron_youtube_scraper_action', raise_if_not_found=False)
        res.update(
            youtube_scraper_interval_number=int(ICPSudo.get_param('youtube_scraper.interval_number', 1)),
            youtube_scraper_interval_type=ICPSudo.get_param('youtube_scraper.interval_type', 'days'),
            youtube_scraper_path=ICPSudo.get_param('youtube_scraper.path', ''),
            youtube_python_executable=ICPSudo.get_param('youtube_scraper.python_executable', 'python3'),
            youtube_scraper_active=cron.active if cron else True,
            youtube_scraper_next_run=cron.nextcall if cron else False,
        )
        return res
