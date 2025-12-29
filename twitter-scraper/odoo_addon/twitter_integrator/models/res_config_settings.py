from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    twitter_scraper_path = fields.Char(
        string="Twitter Scraper Path",
        help="Absolute path to the directory containing main.py",
        config_parameter='twitter.scraper_path'
    )
    
    twitter_python_path = fields.Char(
        string="Python Interpreter Path",
        help="Optional: Absolute path to the python executable. If empty, will auto-detect in venv.",
        config_parameter='twitter.python_path'
    )
    
    twitter_scraper_args = fields.Char(
        string="Additional Arguments",
        help="Additional command line arguments for the scraper (e.g. --headless)",
        config_parameter='twitter.scraper_args'
    )
    
    # Cron Configuration
    scraper_interval_number = fields.Integer(string="Interval Number", default=4, help="Repeat every X units.")
    scraper_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string="Interval Unit", default='hours')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        # Fetch interval from any of the standard scraper crons (fallback to Twitter)
        cron_refs = [
            'twitter_integrator.ir_cron_run_twitter_scraper',
            'tiktok_integrator.ir_cron_run_tiktok_scraper',
            'instagram_integrator.ir_cron_run_instagram_scraper',
            'linkedin_integrator.ir_cron_run_linkedin_scraper',
            'youtube_integrator.ir_cron_run_youtube_scraper',
        ]
        
        for ref in cron_refs:
            cron = self.env.ref(ref, raise_if_not_found=False)
            if cron:
                res.update(
                    scraper_interval_number=cron.interval_number,
                    scraper_interval_type=cron.interval_type,
                )
                break
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        # Update ALL known scraper cron records for unified scheduling
        cron_refs = [
            'twitter_integrator.ir_cron_run_twitter_scraper',
            'tiktok_integrator.ir_cron_run_tiktok_scraper',
            'instagram_integrator.ir_cron_run_instagram_scraper',
            'linkedin_integrator.ir_cron_run_linkedin_scraper',
            'youtube_integrator.ir_cron_run_youtube_scraper',
        ]
        for ref in cron_refs:
            cron = self.env.ref(ref, raise_if_not_found=False)
            if cron:
                cron.sudo().write({
                    'interval_number': self.scraper_interval_number,
                    'interval_type': self.scraper_interval_type,
                })
