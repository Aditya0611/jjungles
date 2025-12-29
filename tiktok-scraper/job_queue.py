"""
Job Queue Manager for Async Retries

This module handles the persistence and retrieval of background jobs using Supabase.
It supports:
- Adding jobs to the queue
- Fetching pending jobs
- Updating job status (success, failure, retry)
- Exponential backoff calculation
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


BASE_RETRY_SECONDS = 60
BACKOFF_MULTIPLIER = 2
MAX_ERROR_LENGTH = 1000
TABLE_NAME = "job_queue"

logger = logging.getLogger(__name__)

@dataclass
class Job:
    id: int
    job_type: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class JobQueue:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.table_name = TABLE_NAME

    def add_job(self, job_type: str, payload: Dict[str, Any], max_attempts: int = 3) -> Optional[int]:
        """Add a new job to the queue."""
        try:
            data = {
                "job_type": job_type,
                "payload": payload,
                "status": "pending",
                "max_attempts": max_attempts,
                "attempts": 0,
                "next_retry_at": datetime.now(timezone.utc).isoformat()
            }
            result = self.supabase.table(self.table_name).insert(data).execute()
            if result.data:
                logger.info(f"Added job {result.data[0]['id']} ({job_type}) to queue")
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Failed to add job to queue: {e}")
            return None

    def fetch_pending_jobs(self, limit: int = 10) -> List[Job]:
        """Fetch pending jobs that are ready to be processed."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            # Fetch pending jobs where next_retry_at <= now
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("status", "pending")\
                .lte("next_retry_at", now)\
                .order("next_retry_at", desc=False)\
                .limit(limit)\
                .execute()

            jobs = []
            for item in result.data:
                jobs.append(self._parse_job(item))
            return jobs
        except Exception as e:
            logger.error(f"Failed to fetch pending jobs: {e}")
            return []

    def mark_processing(self, job_id: int) -> bool:
        """Mark a job as processing."""
        try:
            self.supabase.table(self.table_name)\
                .update({"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()})\
                .eq("id", job_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as processing: {e}")
            return False

    def mark_completed(self, job_id: int) -> bool:
        """Mark a job as completed successfully."""
        try:
            self.supabase.table(self.table_name)\
                .update({"status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()})\
                .eq("id", job_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as completed: {e}")
            return False

    def mark_failed(self, job_id: int, error: str, attempt: int, max_attempts: int) -> bool:
        """Mark a job as failed, scheduling a retry if attempts < max_attempts."""
        try:
            new_attempts = attempt + 1
            if new_attempts < max_attempts:
                # Schedule retry with exponential backoff
                backoff_seconds = BASE_RETRY_SECONDS * (BACKOFF_MULTIPLIER ** (new_attempts - 1))
                next_retry = (datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)).isoformat()
                status = "pending"
                logger.info(f"Scheduling retry for job {job_id} in {backoff_seconds}s (attempt {new_attempts}/{max_attempts})")
            else:
                # Permanent failure
                next_retry = datetime.now(timezone.utc).isoformat() # Doesn't matter much
                status = "failed"
                logger.error(f"Job {job_id} failed permanently after {new_attempts} attempts")

            self.supabase.table(self.table_name).update({
                "status": status,
                "attempts": new_attempts,
                "last_error": str(error)[:MAX_ERROR_LENGTH], 
                "next_retry_at": next_retry,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as failed: {e}")
            return False

    def _parse_job(self, data: Dict[str, Any]) -> Job:
        """Parse DB record into Job object."""
        return Job(
            id=data['id'],
            job_type=data['job_type'],
            payload=data['payload'],
            status=data['status'],
            attempts=data['attempts'],
            max_attempts=data['max_attempts'],
            next_retry_at=datetime.fromisoformat(data['next_retry_at'].replace('Z', '+00:00')),
            last_error=data.get('last_error'),
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
        )
