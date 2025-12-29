from odoo import models, fields, api
import subprocess
import os
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class InstagramScraperConfig(models.Model):
    _name = 'instagram.scraper.config'
    _description = 'Instagram Scraper Configuration'

    name = fields.Char(string='Request Name', required=True, default='Manual Run')
    python_path = fields.Char(string='Python Interpreter Path', default='python', help="Path to python executable")
    interval_number = fields.Integer(string='Interval Number', default=6, help="Repeat every X.")
    interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Interval Unit', default='hours')
    next_call = fields.Datetime(string='Next Execution', related='cron_id.nextcall', readonly=False)
    cron_id = fields.Many2one('ir.cron', string='Scheduled Action', readonly=True)

    # Fields required by view and logic
    script_path = fields.Char(string='Script Path', help="Absolute path to main.py", default='main.py')
    last_run = fields.Datetime(string='Last Execution Time', readonly=True)
    last_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Last Status', readonly=True)
    last_log = fields.Text(string='Execution Log', readonly=True)

    @api.model
    def create(self, vals):
        record = super(InstagramScraperConfig, self).create(vals)
        record._update_cron()
        return record

    def write(self, vals):
        res = super(InstagramScraperConfig, self).write(vals)
        if 'interval_number' in vals or 'interval_type' in vals:
            self._update_cron()
        return res

    def _update_cron(self):
        """Update the associated cron job with new frequency."""
        for record in self:
            cron = record.env.ref('instagram_scraper_odoo.ir_cron_run_scraper', raise_if_not_found=False)
            if not cron:
                # Try to search by name/model if ref not found (e.g. lost xml id)
                cron = self.env['ir.cron'].search([
                    ('model_id.model', '=', 'instagram.scraper.config'),
                    ('state', '=', 'code')
                ], limit=1)
            
            if cron:
                record.cron_id = cron.id
                cron.write({
                    'interval_number': record.interval_number,
                    'interval_type': record.interval_type,
                    'active': True
                })

    def run_scraper(self):
        """Execute the scraper script via subprocess."""
        self.ensure_one()
        _logger.info("Starting Instagram Scraper from Odoo...")
        
        script_path = self.script_path
        if not script_path or not os.path.exists(script_path):
            # Try to resolve relative to current file if default is used
            default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'main.py')
            if os.path.exists(default_path):
                script_path = default_path
            else:
                # Try to find main.py in current directory
                if os.path.exists('main.py'):
                    script_path = os.path.abspath('main.py')
                else:
                    # Log warning but don't hardcode arbitrary path
                    _logger.warning("main.py not found in default locations")
                    script_path = None
        
        if not script_path or not os.path.exists(script_path):
            error_msg = f"Script not found at {script_path}"

            _logger.error(error_msg)
            self.write({
                'last_run': datetime.now(),
                'last_status': 'failed',
                'last_log': error_msg
            })
            return

        try:
            # Run the script using the configured python interpreter
            # We assume environment variables are set or loaded by the script (dotenv)
            # Use --run-once to trigger a single execution
            cmd = [self.python_path, script_path, '--run-once']
            
            # Capture output
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=os.path.dirname(script_path) # Run from script dir to find .env and modules
            )
            
            log_output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            status = 'success' if result.returncode == 0 else 'failed'
            
            self.write({
                'last_run': datetime.now(),
                'last_status': status,
                'last_log': log_output
            })
            
            _logger.info(f"Scraper finished with status: {status}")
            
        except Exception as e:
            _logger.error(f"Scraper execution exception: {e}")
            self.write({
                'last_run': datetime.now(),
                'last_status': 'failed',
                'last_log': str(e)
            })

    @api.model
    def run_cron_scraper(self):
        """Method called by Cron."""
        # Find the first config record or create default
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Scheduled Runner'})
        
        config.run_scraper()
