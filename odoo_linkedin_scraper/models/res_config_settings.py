from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    linkedin_scraper_interval_number = fields.Integer(
        string='LinkedIn Scraper Interval Number', 
        config_parameter='odoo_linkedin_scraper.interval_number',
        default=1
    )
    linkedin_scraper_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='LinkedIn Scraper Interval Unit', 
       config_parameter='odoo_linkedin_scraper.interval_type',
       default='days'
    )
    linkedin_scraper_active = fields.Boolean(
        string='LinkedIn Scraper Active',
        config_parameter='odoo_linkedin_scraper.active',
        default=True
    )
    linkedin_scraper_nextcall = fields.Datetime(
        string='Next Execution',
        config_parameter='odoo_linkedin_scraper.nextcall'
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        
        # Update the cron record dynamically
        cron = self.env.ref('odoo_linkedin_scraper.ir_cron_linkedin_scraper_action', raise_if_not_found=False)
        if cron:
            vals = {
                'interval_number': self.linkedin_scraper_interval_number,
                'interval_type': self.linkedin_scraper_interval_type,
                'active': self.linkedin_scraper_active,
            }
            if self.linkedin_scraper_nextcall:
                vals['nextcall'] = self.linkedin_scraper_nextcall
            cron.write(vals)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        cron = self.env.ref('odoo_linkedin_scraper.ir_cron_linkedin_scraper_action', raise_if_not_found=False)
        if cron:
            res.update({
                'linkedin_scraper_active': cron.active,
                'linkedin_scraper_nextcall': cron.nextcall,
            })
        return res
