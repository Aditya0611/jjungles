"""
Scraper Run Logger - Database logging for job execution tracking.

Provides structured logging to database for:
- Job start/completion tracking
- Success/failure status with counts
- Error message capture
- Performance metrics
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import Client

logger = logging.getLogger(__name__)


class ScraperRunLogger:
    """
    Logs scraper job execution to database.
    Tracks start, progress, and completion of scraper runs.
    """
    
    def __init__(self, supabase: Client, version_id: str):
        """
        Initialize scraper run logger.
        
        Args:
            supabase: Supabase client instance
            version_id: Version ID for this scraper run
        """
        self.supabase = supabase
        self.version_id = version_id
        self.run_id: Optional[int] = None
        self.started_at: Optional[datetime] = None
    
    def start_run(self, config_snapshot: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Log the start of a scraper run.
        
        Args:
            config_snapshot: Optional configuration snapshot
            
        Returns:
            Run ID if successful, None if failed
        """
        try:
            self.started_at = datetime.utcnow()
            
            payload = {
                'started_at': self.started_at.isoformat(),
                'status': 'running',
                'version_id': self.version_id,
                'config_snapshot': config_snapshot or {}
            }
            
            result = self.supabase.table('scraper_runs').insert(payload).execute()
            
            if result.data and len(result.data) > 0:
                self.run_id = result.data[0]['id']
                logger.info(f"Started scraper run {self.run_id}")
                return self.run_id
            else:
                logger.error("Failed to create scraper run record")
                return None
                
        except Exception as e:
            if 'PGRST205' not in str(e) and 'schema cache' not in str(e).lower():
                logger.error(f"Error starting scraper run: {e}")
            return None
    
    def log_step(self, step: str, message: str, level: str = 'INFO', metadata: Optional[Dict] = None):
        """
        Log a step in the scraper run.
        
        Args:
            step: Step name (e.g., 'browser_launch', 'login', 'discovery')
            message: Log message
            level: Log level ('INFO', 'WARNING', 'ERROR', 'DEBUG')
            metadata: Optional metadata dictionary
        """
        if not self.run_id:
            return
        
        try:
            payload = {
                'run_id': self.run_id,
                'timestamp': datetime.utcnow().isoformat(),
                'level': level,
                'message': message,
                'step': step,
                'metadata': metadata or {}
            }
            
            self.supabase.table('scraper_logs').insert(payload).execute()
            
        except Exception as e:
            logger.error(f"Error logging step: {e}")
    
    def complete_run_success(
        self,
        hashtags_discovered: int,
        hashtags_saved: int,
        new_records: int = 0,
        updated_records: int = 0,
        proxy_used: Optional[str] = None,
        proxy_pool_size: Optional[int] = None
    ):
        """
        Mark scraper run as successfully completed.
        
        Args:
            hashtags_discovered: Number of hashtags discovered
            hashtags_saved: Number of hashtags saved to database
            new_records: Number of new records inserted
            updated_records: Number of existing records updated
            proxy_used: Proxy server used (if any)
            proxy_pool_size: Size of proxy pool (if any)
        """
        if not self.run_id:
            return
        
        try:
            completed_at = datetime.utcnow()
            
            payload = {
                'completed_at': completed_at.isoformat(),
                'status': 'success',
                'hashtags_discovered': hashtags_discovered,
                'hashtags_saved': hashtags_saved,
                'new_records': new_records,
                'updated_records': updated_records,
                'proxy_used': proxy_used,
                'proxy_pool_size': proxy_pool_size
            }
            
            self.supabase.table('scraper_runs').update(payload).eq('id', self.run_id).execute()
            
            logger.info(
                f"Scraper run {self.run_id} completed successfully: "
                f"{hashtags_saved} hashtags saved ({new_records} new, {updated_records} updated)"
            )
            
        except Exception as e:
            logger.error(f"Error completing scraper run: {e}")
    
    def complete_run_failure(self, error_message: str, error_type: Optional[str] = None):
        """
        Mark scraper run as failed.
        
        Args:
            error_message: Error message describing the failure
            error_type: Type/category of error (e.g., 'LoginError', 'NetworkError')
        """
        if not self.run_id:
            return
        
        try:
            completed_at = datetime.utcnow()
            
            payload = {
                'completed_at': completed_at.isoformat(),
                'status': 'failed',
                'error_message': error_message,
                'error_type': error_type or 'UnknownError'
            }
            
            self.supabase.table('scraper_runs').update(payload).eq('id', self.run_id).execute()
            
            logger.error(f"Scraper run {self.run_id} failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error marking scraper run as failed: {e}")
    
    def get_recent_runs(self, limit: int = 10) -> list:
        """
        Get recent scraper runs.
        
        Args:
            limit: Number of recent runs to retrieve
            
        Returns:
            List of recent run records
        """
        try:
            result = self.supabase.table('scraper_runs')\
                .select('*')\
                .order('started_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error retrieving recent runs: {e}")
            return []
    
    def get_run_stats(self) -> Dict[str, Any]:
        """
        Get statistics for scraper runs.
        
        Returns:
            Dictionary with run statistics
        """
        try:
            # Get all runs
            all_runs = self.supabase.table('scraper_runs').select('status').execute()
            
            if not all_runs.data:
                return {
                    'total_runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'running_runs': 0,
                    'success_rate': 0.0
                }
            
            total = len(all_runs.data)
            successful = sum(1 for r in all_runs.data if r['status'] == 'success')
            failed = sum(1 for r in all_runs.data if r['status'] == 'failed')
            running = sum(1 for r in all_runs.data if r['status'] == 'running')
            
            success_rate = (successful / total * 100) if total > 0 else 0.0
            
            return {
                'total_runs': total,
                'successful_runs': successful,
                'failed_runs': failed,
                'running_runs': running,
                'success_rate': round(success_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting run stats: {e}")
            return {}
