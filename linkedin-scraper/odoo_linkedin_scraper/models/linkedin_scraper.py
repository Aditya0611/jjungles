import subprocess
import os
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class LinkedInScraper(models.Model):
    _name = 'linkedin.scraper'
    _description = 'LinkedIn Scraper Integration'

    name = fields.Char(string='Run Name', required=True, default=lambda self: fields.Datetime.now())
    status = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='draft')
    
    log_output = fields.Text(string='Log Output')
    records_count = fields.Integer(string='Records Collected')

    def action_run_scraper(self):
        """Method to be called by cron or manually"""
        self.ensure_one()
        self.status = 'running'
        
        # Determine the path to the scraper script
        # Assuming the scraper is in the parent directory of this module
        script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'linkedin_hashtag_scraper_playwright.py')
        
        try:
            # Run the scraper using subprocess
            # We use the current python executable
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            self.log_output = result.stdout + "\n" + result.stderr
            
            if result.returncode == 0:
                self.status = 'success'
                _logger.info("LinkedIn Scraper ran successfully")
            else:
                self.status = 'failed'
                _logger.error("LinkedIn Scraper failed with return code %s", result.returncode)
                
        except Exception as e:
            self.status = 'failed'
            self.log_output = str(e)
            _logger.exception("Error running LinkedIn Scraper")

    @api.model
    def cron_run_scraper(self):
        """Cron entry point"""
        run = self.create({'name': 'Scheduled Run ' + str(fields.Datetime.now())})
        run.action_run_scraper()
