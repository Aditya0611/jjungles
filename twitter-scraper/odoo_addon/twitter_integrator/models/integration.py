from odoo import models, api, fields

class TwitterIntegrator(models.TransientModel):
    _name = 'twitter.integrator'
    _description = 'Twitter Scraper Integration'

    @api.model
    def run_scraper(self):
        """Method called by the Scheduled Action."""
        import subprocess
        import os
        import logging
        import shlex

        _logger = logging.getLogger(__name__)
        
        # 1. Get Configuration
        config = self.env['ir.config_parameter'].sudo()
        base_path = config.get_param('twitter.scraper_path')
        python_path = config.get_param('twitter.python_path')
        scraper_args = config.get_param('twitter.scraper_args', '')
        
        # 2. Env Var Fallback (only for base_path)
        if not base_path:
            base_path = os.getenv('TWITTER_SCRAPER_PATH')
            
        if not base_path:
            _logger.error("Twitter Scraper Path not set! Please configure it in Settings > Technical > Twitter Scraper.")
            return

        current_dir = base_path
        script_path = os.path.join(current_dir, "main.py")
        
        if not os.path.exists(script_path):
             t3_path = os.path.join(current_dir, "t3_scraper.py")
             if os.path.exists(t3_path):
                 script_path = t3_path
             else:
                 _logger.error(f"Scraper script not found at {script_path}")
                 return

        # 3. Determine Python Interpreter
        python_exe = python_path or "python"
        
        # Auto-detect if not explicitly set
        if not python_path:
            possible_paths = [
                os.path.join(current_dir, ".venv", "Scripts", "python.exe"),
                os.path.join(current_dir, ".venv", "bin", "python"),
                os.path.join(current_dir, "venv", "Scripts", "python.exe"),
                os.path.join(current_dir, "venv", "bin", "python"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    python_exe = p
                    break
        
        # 4. Prepare Command
        cmd = [python_exe, script_path]
        if scraper_args:
            args_list = shlex.split(scraper_args)
            cmd.extend(args_list)
            
        _logger.info(f"Running Twitter Scraper: {' '.join(cmd)}")
        
        # 5. Execute Non-Blocking
        try:
            # Platform specific flags for detachment
            kwargs = {}
            if os.name == 'nt':
                # Windows: DETACHED_PROCESS
                # 0x00000008 = DETACHED_PROCESS
                # 0x00000200 = CREATE_NEW_PROCESS_GROUP
                kwargs['creationflags'] = 0x00000008 | 0x00000200 
                kwargs['close_fds'] = True
            else:
                # POSIX: start_new_session
                kwargs['start_new_session'] = True
                
            # Log file for stdout/stderr since we are detaching
            log_file = os.path.join(current_dir, "scraper_execution.log")
            
            # We open files in append mode to capture output
            with open(log_file, "a") as out:
                out.write(f"\n--- Starting Scraper Run at {fields.Datetime.now()} ---\n")
                
                # Use Popen to start immediately and return
                process = subprocess.Popen(
                    cmd,
                    cwd=current_dir,
                    stdout=out,
                    stderr=out,
                    **kwargs
                )
            
            _logger.info(f"Scraper process started (PID: {process.pid}). View details in {log_file}")
            
            # Post a success message to the Odoo log for the record if possible
            # In a real Odoo module, you'd update a log record here.
            
        except Exception as e:
            _logger.error(f"Failed to start scraper process: {str(e)}")
            # We raise here to let Odoo mark the cron as failed if it couldn't even START
            raise

