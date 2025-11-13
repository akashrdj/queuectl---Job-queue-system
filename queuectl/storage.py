

import sqlite3
import threading
from contextlib import contextmanager

from datetime import datetime

from pathlib import Path
from typing import List, Optional

from .models import Job, JobState


class JobStorage:
    
    
    def __init__(self, db_path: str = "queuectl.db"):
        
        self.db_path = db_path
        self._local = threading.local()

        self._init_db()
    
    def _get_connection(self):
        
        if not hasattr(self._local, 'connection'):

            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def _get_cursor(self):
        
        conn = self._get_connection()
        cursor = conn.cursor()
        try:

            yield cursor
            conn.commit()

        except Exception:

            conn.rollback()
            raise
    
    def _init_db(self):
        
        with self._get_cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    output TEXT,
                    error TEXT,
                    exit_code INTEGER,
                    next_retry_at TEXT
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_state ON jobs(state)")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_next_retry ON jobs(next_retry_at)")
    
    def save_job(self, job: Job) -> None:
        
        job.updated_at = datetime.now()
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO jobs 
                (id, command, state, attempts, max_retries, created_at, updated_at, 
                 output, error, exit_code, next_retry_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           
            """, (
                job.jid,
                job.command,
                job.state.value,
                job.attempts,
                job.max_retries,

                job.created_at.isoformat(),
                job.updated_at.isoformat(),

                job.output,
                job.error,
                job.exit_code,
                job.next_retry_at.isoformat() if job.next_retry_at else None
            ))
    
    def get_job(self, job_id: str) -> Optional[Job]:
        
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            
            row = cursor.fetchone()

            
            if row:

                return Job.from_dict(dict(row))
            return None
    
    def list_jobs(self, state: Optional[JobState] = None) -> List[Job]:
        
        with self._get_cursor() as cursor:

            if state:
                cursor.execute(
                    "SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC",
                    (state.value,)
                )

            else:
                cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            
            return [Job.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_pending_job(self) -> Optional[Job]:
        
        with self._get_cursor() as cursor:
            
            cursor.execute("""
                           
                SELECT * FROM jobs 
                WHERE (state = ? OR (state = ? AND next_retry_at <= ?))
                ORDER BY created_at ASC
                LIMIT 1
            """, (JobState.PENDING.value, JobState.FAILED.value, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                job = Job.from_dict(dict(row))
              

                job.state = JobState.PROCESSING
                self.save_job(job)

                return job
            
            return None
    
    def get_job_counts(self) -> dict:
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT state, COUNT(*) as count 
                FROM jobs 
                GROUP BY state
            """)
            
            counts = {state.value: 0 for state in JobState}

            for row in cursor.fetchall():
                counts[row['state']] = row['count']
            
            return counts
    
    def delete_job(self, job_id: str) -> bool:
        
        
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

            return cursor.rowcount > 0
    
    def close(self):
        
        
        if hasattr(self._local, 'connection'):

            self._local.connection.close()
