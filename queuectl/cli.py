
# CLI interface for queuectl

import click
import json
import sys
from datetime import datetime
from pathlib import Path
from tabulate import tabulate
from .storage import JobStorage
from .models import Job, JobState
from .config import Config
from .worker_manager import WorkerManager


@click.group()
@click.version_option(version="1.0.0")
def cli():
    # QueueCTL - A CLI-based background job queue system
    pass


@cli.command()
@click.argument('jsonjob')
@click.option('--db', default='queuectl.db', help='Database path')
def enqueue(jsonjob, db):
    
        #queuectl enqueue '{"id":"job1","command":"sleep 2"}'
   
    try:
        # Parse JSON input
        cleanedjson = jsonjob.strip()
        
        
        if cleanedjson.startswith("'{") and cleanedjson.endswith("}'"):
            cleanedjson = cleanedjson[1:-1]

        elif cleanedjson.startswith("'") and cleanedjson.endswith("'"):
            cleanedjson = cleanedjson[1:-1]
        
        # Parse JSON
        jdata = json.loads(cleanedjson)
        
        # check required fields
        if 'command' not in jdata:



            click.echo("Error: 'command' field is required in JSON", err=True)

            click.echo("Example: queuectl enqueue '{\"id\":\"job1\",\"command\":\"sleep 2\"}'", err=True)
            sys.exit(1)
        
        # unique job id generatgion
        if 'id' not in jdata:
            jdata['id'] = Job.generate_jid()
        
        # default jobs generation
        storage = JobStorage(db)

        config = Config()
        
        job = Job(
            jid=jdata['id'],  # Use jid parameter, read from 'id' key in JSON
            command=jdata['command'],
            state=JobState.PENDING,
            attempts=jdata.get('attempts', 0),

            max_retries=jdata.get('max_retries', config.get('max_retries', 3)),

            created_at=datetime.utcnow() if 'created_at' not in jdata else datetime.fromisoformat(jdata['created_at']),
            updated_at=datetime.utcnow() if 'updated_at' not in jdata else datetime.fromisoformat(jdata['updated_at'])

        )
        
        storage.save_job(job)
        click.echo(f" Job {job.jid} enqueued successfully")  # Use job.jid
    
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON format - {e}", err=True)
        #
        click.echo("\nUsage: queuectl enqueue '{\"id\":\"job1\",\"command\":\"sleep 2\"}'", err=True)
        sys.exit(1)


    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    # Manage worker processes
    pass


@worker.command()
@click.option('--count', default=1, help='Number of workers to start')

@click.option('--db', default='queuectl.db', help='Database path')

@click.option('--background/--foreground', default=True, help='Run in background (default) or foreground')
def start(count, db, background):
    # start process
    manager = WorkerManager(db)
    
    if background:
        
        click.echo(f"Starting {count} worker(s) in background...")

        manager.start_workers_background(count)
        click.echo(f" Started {count} worker(s)")



        click.echo(f"  Run 'queuectl worker status' to check statos .")

        click.echo(f"  Run 'queuectl worker stop' to stop them .")
    else:
        # run  until Ctrl+C
        click.echo(f"Starting {count} worker(s) in foreground (Press Ctrl+C to stop)...")


        manager.start_workers(count)


@worker.command()
@click.option('--db', default='queuectl.db', help='Database path')
def stop(db):
    # stop process

    manager = WorkerManager(db)

    manager.stop_workers()


@worker.command()
@click.option('--db', default='queuectl.db', help='Database path')
def status(db):
    # show stats
    manager = WorkerManager(db)


    status = manager.get_workstats()
    
    click.echo(f"\n{'=' * 50}")
    click.echo("WORKER STATUS")

    click.echo(f"{'=' * 50}")

    click.echo(f"Active Workers: {status['active_workers']}")
    
    if status['worker_pids']:
        click.echo(f"PIDs: {', '.join(map(str, status['worker_pids']))}")
    else:
        click.echo("No active workers")
    click.echo()


@cli.command()
@click.option('--db', default='queuectl.db', help='Database path')
def status(db):
    # summary of wokrs



    storage = JobStorage(db)
    manager = WorkerManager(db)
    
    # Get counts
    counts = storage.get_job_counts()
    
    # worker status
    workstats = manager.get_workstats()
    
    # Display summary
    click.echo(f"\n{'=' * 50}")
    click.echo("QUEUECTL STATUS")


    click.echo(f"{'=' * 50}")
    click.echo(f"\nActive Workers: {workstats['active_workers']}")
    
    if workstats['worker_pids']:
        click.echo(f"Worker PIDs: {', '.join(map(str, workstats['worker_pids']))}")
    
    click.echo(f"\n{'JOB SUMMARY':-^50}")
    tabledata = []
    for state in JobState:
        count = counts.get(state.value, 0)
        tabledata.append([state.value.upper(), count])
    
    click.echo(tabulate(tabledata, headers=['State', 'Count'], tablefmt='grid'))
    click.echo()


@cli.command()
@click.option('--state', help='Filter by job state (pending, processing, completed, failed, dead)')


@click.option('--db', default='queuectl.db', help='Database path')
def list(state, db):
    """List jobs, optionally filtered by state"""
    storage = JobStorage(db)
    
    if state:
        # chekc state
        validstates = [s.value for s in JobState]
        if state not in validstates:
            click.echo(f"Error: Invalid state. Must be one of: {', '.join(validstates)}", err=True)
            sys.exit(1)

        jobs = storage.list_jobs(JobState(state)) 


        title = f"JOBS - {state.upper()}"
    else:
        jobs = storage.list_jobs() 


        title = "ALL JOBS"
    
    if not jobs:
        click.echo(f"\nNo jobs found{' with state ' + state if state else ''}")
        return
    
    click.echo(f"\n{title:-^80}")
    
    tabledata = []
    for job in jobs:
        tabledata.append([
            job.jid[:12] + '...' if len(job.jid) > 12 else job.jid,


            job.command[:30] + '...' if len(job.command) > 30 else job.command,
            job.state.value,
            f"{job.attempts}/{job.max_retries}",


            str(job.created_at)[:19] if job.created_at else '-',
            (job.error[:30] + '...' if job.error and len(job.error) > 30 
             else job.error or '-')
        ])
    
    headers = ['Job ID', 'Command', 'State', 'Attempts', 'Created', 'Error']


    click.echo(tabulate(tabledata, headers=headers, tablefmt='grid'))
    click.echo(f"\nTotal: {len(jobs)} job(s)\n")


@cli.group()
def dlq():
    # Dead Letter Queue management
    pass


@dlq.command()
@click.option('--db', default='queuectl.db', help='Database path')
def list(db):
    
    storage = JobStorage(db)


    jobs = storage.list_jobs(JobState.DEAD)  
    
    if not jobs:
        click.echo("\nNo jobs in Dead Letter Queue")

        return
    
    click.echo(f"\n{'DEAD LETTER QUEUE':-^80}")
    
    tabledata = []
    for job in jobs:


        tabledata.append([
            job.jid[:12] + '...' if len(job.jid) > 12 else job.jid,
            job.command[:30] + '...' if len(job.command) > 30 else job.command,
            job.attempts,

            str(job.created_at)[:19] if job.created_at else '-',
            (job.error[:40] + '...' if job.error and len(job.error) > 40 
             else job.error or '-')
        ])
    
    headers = ['Job ID', 'Command', 'Attempts', 'Created', 'Last Error']

    click.echo(tabulate(tabledata, headers=headers, tablefmt='grid'))
    click.echo(f"\nTotal: {len(jobs)} job(s) in DLQ\n")


@dlq.command()
@click.argument('jid')
@click.option('--db', default='queuectl.db', help='Database path')
def retry(jid, db):
    # Retry  from t Dead Letter Queue
    storage = JobStorage(db)

    job = storage.get_job(jid)
    
    if not job:
        click.echo(f"Error: Job {jid} not found", err=True)
        sys.exit(1)
    
    if job.state != JobState.DEAD:


        click.echo(f"Error: Job {jid} is not in DLQ (current state: {job.state.value})", err=True)
        sys.exit(1)
    
    # reset
    job.state = JobState.PENDING 
    job.attempts = 0
    job.error = None  
    job.next_retry_at = None
    job.updated_at = datetime.utcnow()
    
    storage.save_job(job)  #

    click.echo(f" Job {jid} moved from DLQ to pending queue")


@dlq.command()
@click.argument('jid')

@click.option('--db', default='queuectl.db', help='Database path')
def remove(jid, db):

    
    storage = JobStorage(db)
    job = storage.get_job(jid)
    
    if not job:
        click.echo(f"Error: Job {jid} not found", err=True)

        sys.exit(1)
    
    if job.state != JobState.DEAD:

        click.echo(f"Error: Job {jid} is not in DLQ (current state: {job.state.value})", err=True)
        sys.exit(1)
    
    storage.delete_job(jid)
    click.echo(f" Job {jid} removed from DLQ")


@cli.group()
def config():

    # config management
    pass


@config.command()
@click.argument('key')
@click.argument('value')

@click.option('--db', default='queuectl.db', help='Database path')
def set(key, value, db):
    
    config = Config()  
    
    kmap = {
        'max-retries': 'max_retries',
        'backoff-base': 'backoff_base',
        'worker-poll-interval': 'worker_poll_interval'
    }
    
    if key not in kmap:
        click.echo(f"Error: Invalid config key. check: {', '.join(kmap.keys())}", err=True)
        sys.exit(1)
    
    try:
        value = int(value)
        config.set(kmap[key], value)  

        click.echo(f" Configuration updated: {key} = {value}")

    except ValueError:
        click.echo(f"Error: Value must be an integer", err=True)
        sys.exit(1)


@config.command()
@click.option('--db', default='queuectl.db', help='Database path')
def show(db):
    
    config = Config()  
    
    click.echo(f"\n{'CONFIGURATION':-^50}")
    tabledata = [
        ['max-retries', config.get('max_retries')],
        ['backoff-base', config.get('backoff_base')],
        ['db-path', config.get('db_path')]
    ]
    click.echo(tabulate(tabledata, headers=['Key', 'Value'], tablefmt='grid'))
    click.echo()


@cli.command()
@click.argument('jid')
@click.option('--db', default='queuectl.db', help='Database path')
def info(jid, db):
    # show info
    storage = JobStorage(db)
    job = storage.get_job(jid)
    
    if not job:
        click.echo(f"Error: Job {jid} not found", err=True)
        sys.exit(1)
    
    click.echo(f"\n{'JOB DETAILS':-^80}")
    details = [
        ['ID', job.jid],
        ['Command', job.command],

        ['State', job.state.value],  # Use .value for enum
        ['Attempts', f"{job.attempts}/{job.max_retries}"],

        ['Created At', job.created_at.isoformat() if hasattr(job.created_at, 'isoformat') else job.created_at],
        
        ['Updated At', job.updated_at.isoformat() if hasattr(job.updated_at, 'isoformat') else job.updated_at],
        ['Exit Code', job.exit_code if job.exit_code is not None else '-'],


        ['Next Retry At', job.next_retry_at.isoformat() if job.next_retry_at and hasattr(job.next_retry_at, 'isoformat') else (job.next_retry_at or '-')],
        ['Error', job.error or '-']  # Use 'error' field
    ]
    click.echo(tabulate(details, tablefmt='grid'))
    click.echo()


def main():
    
    cli()


if __name__ == '__main__':
    main()
