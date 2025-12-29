# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SchedulerSettings(models.Model):
    _name = 'scheduler.settings'
    _description = 'Scraper Scheduler Settings'
    _rec_name = 'platform'

    platform = fields.Selection([
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
    ], string='Platform', required=True)
    
    enabled = fields.Boolean(
        string='Enabled',
        default=True,
        help='Enable or disable scraping for this platform'
    )
    
    frequency_hours = fields.Float(
        string='Frequency (Hours)',
        default=3.0,
        required=True,
        help='How often to scrape this platform (in hours). Min: 0.5, Max: 24.0'
    )
    
    metadata = fields.Json(
        string='Metadata',
        default=lambda self: {
            'region': 'en',
            'headless': True,
            'upload_to_db': True
        }
    )
    
    last_run_at = fields.Datetime(
        string='Last Run',
        readonly=True
    )
    
    next_run_at = fields.Datetime(
        string='Next Run',
        readonly=True
    )
    
    run_count = fields.Integer(
        string='Total Runs',
        default=0,
        readonly=True
    )
    
    success_count = fields.Integer(
        string='Successful Runs',
        default=0,
        readonly=True
    )
    
    failure_count = fields.Integer(
        string='Failed Runs',
        default=0,
        readonly=True
    )
    
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        store=True
    )
    
    @api.depends('run_count', 'success_count')
    def _compute_success_rate(self):
        for record in self:
            if record.run_count > 0:
                record.success_rate = (record.success_count / record.run_count) * 100
            else:
                record.success_rate = 0.0
    
    @api.constrains('frequency_hours')
    def _check_frequency_hours(self):
        for record in self:
            if record.frequency_hours < 0.5 or record.frequency_hours > 24.0:
                raise ValidationError(
                    'Frequency must be between 0.5 and 24.0 hours.'
                )
    
    @api.model
    def sync_to_supabase(self):
        """Sync settings to Supabase for worker to pick up."""
        import os
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # Get Supabase credentials from environment or config
            supabase_url = os.environ.get('SUPABASE_URL')
            supabase_key = os.environ.get('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                _logger.warning("Supabase credentials not configured, skipping sync")
                return
            
            # Import Supabase client
            try:
                from supabase import create_client
            except ImportError:
                _logger.error("Supabase Python client not installed. Install with: pip install supabase")
                return
            
            # Create Supabase client
            supabase = create_client(supabase_url, supabase_key)
            
            # Get all scheduler settings
            settings = self.search([])
            
            for setting in settings:
                # Prepare data for Supabase
                data = {
                    'platform': setting.platform,
                    'enabled': setting.enabled,
                    'frequency_hours': setting.frequency_hours,
                    'metadata': setting.metadata or {},
                    'last_run_at': setting.last_run_at.isoformat() if setting.last_run_at else None,
                    'next_run_at': setting.next_run_at.isoformat() if setting.next_run_at else None,
                    'run_count': setting.run_count,
                    'success_count': setting.success_count,
                    'failure_count': setting.failure_count,
                }
                
                # Upsert to Supabase scheduler_settings table
                try:
                    result = supabase.table('scheduler_settings').upsert(
                        data,
                        on_conflict='platform'
                    ).execute()
                    _logger.info(f"Synced {setting.platform} settings to Supabase")
                except Exception as e:
                    _logger.error(f"Failed to sync {setting.platform} to Supabase: {e}")
            
            _logger.info(f"Successfully synced {len(settings)} platform settings to Supabase")
            
        except Exception as e:
            _logger.error(f"Error in sync_to_supabase: {e}")
    
    def write(self, vals):
        """Override write to sync to Supabase on changes."""
        result = super(SchedulerSettings, self).write(vals)
        # Trigger sync to Supabase here
        self.sync_to_supabase()
        return result
    
    def action_enable(self):
        """Enable the platform scraper."""
        self.write({'enabled': True})
    
    def action_disable(self):
        """Disable the platform scraper."""
        self.write({'enabled': False})
    
    def action_process_queue(self):
        """Manually trigger the background queue worker."""
        self.ensure_one()
        self.run_queue_worker_job()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Queue Worker Started',
                'message': 'The background queue worker has been triggered to process pending uploads and retries.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def run_queue_worker_job(self):
        """Run the backend queue worker (offline uploads and retries)."""
        import subprocess
        import logging
        import os
        import sys
        from pathlib import Path
        _logger = logging.getLogger(__name__)
        
        try:
            # Detect base path
            base_path = os.environ.get('SCRAPER_BASE_PATH')
            if not base_path:
                cwd = Path(os.getcwd())
                candidates = [
                    cwd,
                    cwd / '..',
                    cwd / 'social_media_scraper', # If running from odoo addons
                    Path(__file__).parent.parent.parent.parent,
                    Path('/opt/scraper')
                ]
                for candidate in candidates:
                    if (candidate / 'offline_queue_worker.py').exists():
                        base_path = str(candidate.resolve())
                        break
            
            if not base_path:
                _logger.error("Could not locate offline_queue_worker.py")
                return

            cmd = [
                sys.executable,
                os.path.join(base_path, 'offline_queue_worker.py'),
                '--run-once'
            ]
            
            # Use Popen to run in background if called from UI to avoid blocking
            # But for cron, we might want to wait. 
            # We'll use subprocess.run with a short timeout as a middle ground for now
            # or just detach it.
            _logger.info(f"Running queue worker: {' '.join(cmd)}")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        except Exception as e:
            _logger.error(f"Error in run_queue_worker_job: {e}")

    @api.model
    def run_scraper_job(self, platform):
        """Run scraper job for a specific platform."""
        import subprocess
        import logging
        import os
        import sys
        from pathlib import Path
        _logger = logging.getLogger(__name__)
        
        try:
            # Find the platform setting
            setting = self.search([('platform', '=', platform)], limit=1)
            
            if not setting:
                _logger.warning(f"No scheduler setting found for platform: {platform}")
                return
            
            if not setting.enabled:
                _logger.info(f"Scraper for {platform} is disabled, skipping")
                return
            
            _logger.info(f"Triggering scraper for {platform}")
            
            # Get metadata
            metadata = setting.metadata or {}
            region = metadata.get('region', 'en')
            headless = metadata.get('headless', True)
            upload_to_db = metadata.get('upload_to_db', True)
            
            # Trigger scraper via subprocess (non-blocking)
            try:
                # Locate base.py
                base_path = os.environ.get('SCRAPER_BASE_PATH')
                
                # If env var not set, try to find it relative to this file or cwd
                if not base_path:
                    # Possible locations:
                    # 1. Current working directory (e.g. if running odoo-bin from project root)
                    # 2. Parent directories (if running deep in module)
                    # 3. /opt/scraper (common deployment path)
                    
                    cwd = Path(os.getcwd())
                    candidates = [
                        cwd,
                        cwd / '..',
                        cwd / '..' / '..',
                        Path(__file__).parent.parent.parent.parent, # Assuming models/../../.. -> root
                        Path('/opt/scraper')
                    ]
                    
                    for candidate in candidates:
                        check_path = candidate.resolve() / 'base.py'
                        if check_path.exists():
                            base_path = str(candidate.resolve())
                            _logger.info(f"Found scraper at: {base_path}")
                            break
                
                if not base_path:
                    _logger.error("Could not locate base.py. Set SCRAPER_BASE_PATH or ensure it's in a standard location.")
                    return

                script_path = os.path.join(base_path, 'base.py')
                
                # Use the same python interpreter
                python_exe = sys.executable

                cmd = [
                    python_exe,
                    script_path,
                    '--platform', platform,
                    '--region', region,
                    '--headless' if headless else '--no-headless',
                    '--upload' if upload_to_db else '--no-upload'
                ]
                
                # Run in background
                subprocess.Popen(cmd)
                _logger.info(f"Scraper job started for {platform} (PID unknown, detached)")
                
                # Update last_run_at
                setting.write({'last_run_at': fields.Datetime.now()})
                
            except Exception as e:
                _logger.error(f"Failed to start scraper for {platform}: {e}")
                
        except Exception as e:
            _logger.error(f"Error in run_scraper_job for {platform}: {e}")
    
    @api.model
    def update_cron_intervals(self):
        """Update cron job intervals based on scheduler settings."""
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # Get all scheduler settings
            settings = self.search([])
            
            # Map platform to cron external ID
            platform_cron_map = {
                'tiktok': 'social_media_scraper.ir_cron_run_tiktok_scraper',
                'instagram': 'social_media_scraper.ir_cron_run_instagram_scraper',
            }
            
            for setting in settings:
                cron_xml_id = platform_cron_map.get(setting.platform)
                
                if not cron_xml_id:
                    continue
                
                try:
                    # Get the cron job
                    cron = self.env.ref(cron_xml_id, raise_if_not_found=False)
                    
                    if not cron:
                        _logger.warning(f"Cron job not found: {cron_xml_id}")
                        continue
                    
                    # Update interval based on frequency_hours
                    frequency_hours = setting.frequency_hours
                    
                    # Convert to hours/minutes
                    if frequency_hours >= 1.0:
                        interval_number = int(frequency_hours)
                        interval_type = 'hours'
                    else:
                        interval_number = int(frequency_hours * 60)
                        interval_type = 'minutes'
                    
                    # Update cron job
                    cron.write({
                        'interval_number': interval_number,
                        'interval_type': interval_type,
                        'active': setting.enabled
                    })
                    
                    _logger.info(f"Updated cron for {setting.platform}: {interval_number} {interval_type}, active={setting.enabled}")
                    
                except Exception as e:
                    _logger.error(f"Failed to update cron for {setting.platform}: {e}")
            
            _logger.info("Cron intervals updated successfully")
            
        except Exception as e:
            _logger.error(f"Error in update_cron_intervals: {e}")
