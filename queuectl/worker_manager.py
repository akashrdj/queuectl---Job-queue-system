

import json
import multiprocessing
import os
import signal
import subprocess

import sys
import time
from pathlib import Path

from typing import List

from .config import Config
from .worker import start_worker


class WorkerManager:
    
    
    def __init__(self, db_path: str = "queuectl.db"):
        self.db_path = db_path
        self.workers: List[multiprocessing.Process] = []
        
        self.pid_file = "queuectl_workers.pid"
    
    def start_workers(self, count: int = 1):
        
        for i in range(count):
            process = multiprocessing.Process(
                target=start_worker,

                args=(self.db_path,),

                daemon=False
            )
            process.start()
            self.workers.append(process)

            print(f"Started worker process {process.pid}")
        
        # Save PIDs to file
        self.savepid()
        
        print(f"Started {count} worker(s)")
        
        # Wait for workers (foreground mode)
        try:
            for worker in self.workers:
                worker.join()
        except KeyboardInterrupt:
            print("\nStopping workers...")
            self.stop_workers()
    
    def startworkbackground(self, count: int = 1):
        
        import subprocess
        import sys
        
        pids = []
        for i in range(count):
            if sys.platform == 'win32':
                # Windows: detached process
                proc = subprocess.Popen(

                    [sys.executable, '-c', 
                     f'from queuectl.worker import start_worker; start_worker("{self.db_path}")'],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,

                    stderr=subprocess.DEVNULL,

                    stdin=subprocess.DEVNULL
                )
            else:
                # Unix: background process
                proc = subprocess.Popen(
                    [sys.executable, '-c',
                     f'from queuectl.worker import start_worker; start_worker("{self.db_path}")'],
                    stdout=subprocess.DEVNULL,

                    stderr=subprocess.DEVNULL,

                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )
            pids.append(proc.pid)
        
        # Save PIDs
        self.savepid(pids)
    
    def stop_workers(self):
       
        pids = self.loadpid()
        
        if not pids:

            print("No running workers found")

            return
        
        stopped = 0

        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)

                print(f"Sent stop signal to worker {pid}")

                stopped += 1
            except ProcessLookupError:

                print(f"Worker {pid} not found (already stopped)")
            except Exception as e:

                print(f"Error stopping worker {pid}: {e}")
        
        if stopped > 0:
            print(f"Stopped {stopped} worker(s). They will finish their current jobs and exit.")
        
        # Clean up PID file
        self.clearpid()
    
    def workerstatus(self) -> dict:
        
        import sys

        import psutil
        
        pids = self.loadpid()
        
        active_pids = []
        for pid in pids:
            try:
                
                if psutil.pid_exists(pid):

                    active_pids.append(pid)

            except Exception:
                pass
        
        
        if len(active_pids) != len(pids):

            self.savepid(active_pids)
        
        return {
            "active_workers": len(active_pids),

            "worker_pids": active_pids
        }
    
    def savepid(self, pids: List[int] = None):
        
        if pids is None:
            pids = [w.pid for w in self.workers]
        
        with open(self.pid_file, 'w') as f:

            f.write('\n'.join(map(str, pids)))
    
    def loadpid(self) -> List[int]:
        
        if not os.path.exists(self.pid_file):

            return []
        
        try:
            with open(self.pid_file, 'r') as f:

                return [int(line.strip()) for line in f if line.strip()]
        except Exception:
            return []
    
    def clearpid(self):
        
        if os.path.exists(self.pid_file):

            os.remove(self.pid_file)
