

import signal
import subprocess
import time
from datetime import datetime, timedelta

from .config import Config
from .models import Job, JobState
from .storage import JobStorage


class Worker:
    
    
    def __init__(self, worker_id: int, db_path: str, config: Config):
        
        self.worker_id = worker_id
        self.storage = JobStorage(db_path)

        self.config = config
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signalhandler)

        signal.signal(signal.SIGTERM, self.signalhandler)
    
    def signalhandler(self, signum, frame):
        
        print(f"\n[Worker {self.worker_id}] Received shutdown signal, finishing current job...")
        self.running = False
    
    def stop(self):
        
        print(f"[Worker {self.worker_id}] Stop requested")
        self.running = False
    
    def executecommand(self, command: str) -> tuple:

        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,

                text=True,

                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:

            return -1, "", "Command timed out after 300 seconds"
        except Exception as e:

            return -1, "", str(e)
    
    def calbackoff(self, attempts: int) -> float:
       
        base = self.config.get('backoff_base', 2)

        return base ** attempts
    
    def processjob(self, job: Job) -> None:
       
        print(f"[Worker {self.worker_id}] Processing job {job.jid}: {job.command}")
        

        job.attempts += 1
        job.state = JobState.PROCESSING

        self.storage.save_job(job)
        
        # Execute the command
        exit_code, output, error = self.executecommand(job.command)
        
        job.exit_code = exit_code

        job.output = output if output else None

        job.error = error if error else None
        
        if exit_code == 0:
            # Success
            job.state = JobState.COMPLETED
            print(f"[Worker {self.worker_id}]  Job {job.jid} completed successfully")
        else:
            # Failure
            max_retries = self.config.get('max_retries', 3)
            
            if job.attempts >= max_retries:
                # Move to DLQ
                job.state = JobState.DEAD
                print(f"[Worker {self.worker_id}]  Job {job.jid} moved to DLQ after {job.attempts} attempts")
            else:
                # Retry with backoff
                job.state = JobState.FAILED
                backoff_seconds = self.calbackoff(job.attempts)
                job.next_retry_at = datetime.now() + timedelta(seconds=backoff_seconds)

                print(f"[Worker {self.worker_id}]  Job {job.jid} failed (attempt {job.attempts}/{max_retries}), retry in {backoff_seconds}s")
        
        self.storage.save_job(job)
    
    def run(self):
        
        print(f"[Worker {self.worker_id}] Started and ready to process jobs")
        
        while self.running:
            try:
                # Get next pending job
                job = self.storage.get_pending_job()
                
                if job:
                    self.processjob(job)
                else:
                    # No jobs available, sleep briefly
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[Worker {self.worker_id}] Error: {e}")

                time.sleep(1)
        
        print(f"[Worker {self.worker_id}] Stopped gracefully")

        self.storage.close()


def start_worker(db_path: str, worker_id: int = 1):
    
    config = Config()

    worker = Worker(worker_id, db_path, config)
    worker.run()
