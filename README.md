# QueueCTL - CLI-Based Background Job Queue System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade, CLI-based background job queue system with worker processes, automatic retries with exponential backoff, and a Dead Letter Queue (DLQ) for permanently failed jobs.

## 🎯 Features

- ✅ **CLI Interface** - Complete command-line interface for all operations
- ✅ **Background Job Queue** - Enqueue and manage jobs asynchronously  
- ✅ **Multi-Worker Support** - Run multiple worker processes in parallel
- ✅ **Automatic Retry** - Failed jobs retry with exponential backoff
- ✅ **Dead Letter Queue (DLQ)** - Permanently failed jobs moved to DLQ
- ✅ **Persistent Storage** - SQLite database survives restarts
- ✅ **Graceful Shutdown** - Workers finish current job before stopping
- ✅ **Configurable** - Customize retry count, backoff, and more
- ✅ **Race Condition Safe** - Prevents duplicate job processing

## 📋 Requirements

- Python 3.8 or higher
- pip (Python package manager)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/queuectl.git
cd queuectl

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### 2. Basic Usage

**⚠️ Important: QueueCTL only accepts JSON format for enqueuing jobs**

```bash
# Enqueue a job (JSON format required)
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'

# Start workers
queuectl worker start --count 2

# Check status
queuectl status

# List all jobs
queuectl list

# Stop workers
queuectl worker stop
```

## 📖 Detailed Usage

### Enqueue Jobs

**⚠️ IMPORTANT: QueueCTL only accepts JSON format for job submission**

**JSON Format (Required):**
```bash
# Basic job with auto-generated ID
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'

# Job with custom max retries
queuectl enqueue '{"id":"job2","command":"sleep 5","max_retries":5}'

# Job with special characters (Windows PowerShell)
queuectl enqueue '{"id":"job3","command":"echo \"Hello World\""}'
```

**Job JSON Structure:**
```json
{
  "id": "unique-job-id",       # Required: Unique job identifier
  "command": "echo 'Hello'",   # Required: Shell command to execute
  "max_retries": 3             # Optional: Override default retry count
}
```

**Platform-Specific Notes:**
- **Windows PowerShell**: Use single quotes for outer JSON, double quotes inside
- **Linux/Mac**: Use single quotes for outer JSON
- **Windows CMD**: May need to escape quotes differently

### Manage Workers

```bash
# Start workers in background (default)
queuectl worker start --count 3

# Start in foreground (blocks until Ctrl+C)
queuectl worker start --count 2 --foreground

# Check worker status
queuectl worker status

# Stop all workers gracefully
queuectl worker stop
```

**Worker Options:**
- `--count N` : Number of worker processes (default: 1)
- `--foreground` : Run in foreground mode (Ctrl+C to stop)

### Check Status

```bash
# Show overall status
queuectl status

# Example output:
==================================================
QUEUECTL STATUS
==================================================

Active Workers: 2
Worker PIDs: 12345, 12346

                JOB SUMMARY                
+------------+-------+
| State      | Count |
+============+=======+
| PENDING    |     3 |
| PROCESSING |     1 |
| COMPLETED  |    15 |
| FAILED     |     2 |
| DEAD       |     1 |
+------------+-------+
```

### List Jobs

```bash
# List all jobs
queuectl list

# Filter by state
queuectl list --state pending
queuectl list --state completed
queuectl list --state failed
queuectl list --state dead

# Get detailed job information
queuectl info <job-id>
```

### Dead Letter Queue (DLQ)

```bash
# List jobs in DLQ
queuectl dlq list

# Retry a DLQ job (moves back to queue)
queuectl dlq retry <job-id>

# Remove a job from DLQ permanently
queuectl dlq remove <job-id>
```

### Configuration

**⚠️ IMPORTANT: Use hyphens (-) not underscores (_) in config keys**

```bash
# View current configuration
queuectl config show

# Set maximum retry attempts (use hyphen!)
queuectl config set max-retries 5

# Set exponential backoff base (use hyphen!)
queuectl config set backoff-base 3

# Example output:
                CONFIGURATION                
+--------------+-------------+
| Key          | Value       |
+==============+=============+
| max-retries  |     5       |
| backoff-base |     3       |
| db-path      | queuectl.db |
+--------------+-------------+
```

**Available Config Keys:**
- `max-retries` - Maximum retry attempts before DLQ (NOT max_retries)
- `backoff-base` - Exponential backoff base multiplier (NOT backoff_base)
- `db-path` - Database file path (NOT db_path)

## 🏗️ Architecture Overview

### System Components

```
┌─────────────┐
│   CLI       │ ← User Interface
└─────┬───────┘
      │
┌─────▼────────────────────────────────────┐
│         Job Storage (SQLite)             │
│  - Jobs Table                            │
│  - Configuration                         │
│  - Thread-safe operations                │
└─────┬────────────────────────────────────┘
      │
┌─────▼───────────────────────────────────┐
│      Worker Manager                     │
│  - Spawn/Stop workers                   │
│  - Process management                   │
└─────┬───────────────────────────────────┘
      │
┌─────▼──────────┬──────────┬─────────────┐
│   Worker 1     │ Worker 2 │  Worker N   │
│  - Get jobs    │          │             │
│  - Execute     │          │             │
│  - Retry logic │          │             │
└────────────────┴──────────┴─────────────┘
```

### Job Lifecycle

```
  PENDING
     │
     ▼
  PROCESSING ──(success)──> COMPLETED
     │
     │ (failure)
     ▼
   FAILED ──(retry with backoff)──> PENDING
     │
     │ (max retries exceeded)
     ▼
   DEAD (DLQ)
```

### Retry Mechanism

Failed jobs automatically retry with **exponential backoff**:

```
Delay = base ^ attempts (in seconds)

With base=2 (default):
- Attempt 1: Immediate
- Attempt 2: After 2 seconds  (2^1)
- Attempt 3: After 4 seconds  (2^2)
- Attempt 4: After 8 seconds  (2^3)
```

After `max_retries` (default: 3), jobs move to **Dead Letter Queue**.

### Data Persistence

- **Database**: SQLite (`queuectl.db`)
- **Config**: JSON file (`queuectl_config.json`)
- **Worker PIDs**: Text file (`queuectl_workers.pid`)

All data persists across restarts.

### Concurrency & Race Conditions

**Problem**: Multiple workers accessing same job simultaneously

**Solution**: Database-level locking
- Jobs marked as `PROCESSING` immediately upon fetch
- SQLite transaction isolation prevents duplicate reads
- Workers only see `PENDING` or retryable `FAILED` jobs

## 🧪 Testing

### Automated Test Suite

```bash
# Run comprehensive test suite
python test_queuectl.py
```

**Tests cover:**
1. ✅ Basic job enqueue
2. ✅ JSON job enqueue
3. ✅ List jobs
4. ✅ Show status
5. ✅ Configuration management
6. ✅ Worker lifecycle
7. ✅ Failed job retry with exponential backoff
8. ✅ DLQ retry functionality
9. ✅ Data persistence
10. ✅ Concurrent workers without duplication

### Manual Testing Scenarios

#### Test 1: Basic Job Completes Successfully
```bash
# Enqueue a simple job (JSON format required)
queuectl enqueue '{"id":"test-success","command":"echo Success"}'

# Start worker
queuectl worker start --count 1

# Wait and check status (should show 1 completed)
# On Windows PowerShell: Start-Sleep -Seconds 3
# On Linux/Mac: sleep 3

queuectl status
queuectl list --state completed

# Stop worker
queuectl worker stop
```

#### Test 2: Failed Job Retries and Moves to DLQ
```bash
# Enqueue a failing job (Windows: cmd /c exit 1, Linux: exit 1)
queuectl enqueue '{"id":"fail-test","command":"cmd /c exit 1","max_retries":3}'

# Start worker
queuectl worker start --count 1

# Watch retry attempts (with exponential backoff: 2s, 4s, 8s)
# Total wait: ~15 seconds for 3 retries
# Wait 20 seconds

# Check DLQ
queuectl dlq list

# Should show fail-test job in DLQ
queuectl worker stop
```

#### Test 3: Multiple Workers Process Jobs Without Overlap
```bash
# Enqueue 10 jobs (Windows PowerShell)
for ($i=1; $i -le 10; $i++) {
  queuectl enqueue "{`"id`":`"job-$i`",`"command`":`"echo Job $i`"}"
}

# Linux/Mac:
# for i in {1..10}; do
#   queuectl enqueue "{\"id\":\"job-$i\",\"command\":\"echo Job $i\"}"
# done

# Start 3 workers
queuectl worker start --count 3

# Monitor processing
queuectl status

# Wait for completion (10 seconds)

# Verify all completed
queuectl list --state completed

# Stop workers
queuectl worker stop
```

#### Test 4: Invalid Commands Fail Gracefully
```bash
# Enqueue invalid command
queuectl enqueue '{"id":"invalid-cmd","command":"nonexistent_command_xyz"}'

# Start worker
queuectl worker start --count 1

# Wait for retries (20 seconds)

# Check DLQ (should contain failed job)
queuectl dlq list

queuectl worker stop
```

#### Test 5: Job Data Survives Restart
```bash
# Enqueue jobs
queuectl enqueue '{"id":"persist-1","command":"echo Test 1"}'
queuectl enqueue '{"id":"persist-2","command":"echo Test 2"}'

# Verify jobs exist
queuectl list

# Simulate restart (close terminal, reopen)

# Check jobs still exist
queuectl list

# Should still show persist-1 and persist-2
```

## ⚙️ Configuration Options

**⚠️ IMPORTANT: Always use hyphens (-) in config keys, NOT underscores (_)**

| Key | Default | Description |
|-----|---------|-------------|
| `max-retries` | 3 | Maximum retry attempts before moving to DLQ |
| `backoff-base` | 2 | Base for exponential backoff calculation |
| `db-path` | queuectl.db | SQLite database file path |

### Changing Configuration

```bash
# ✅ CORRECT: Use hyphens
queuectl config set max-retries 5
queuectl config set backoff-base 3

# ❌ WRONG: Don't use underscores
queuectl config set max_retries 5  # This will fail!
queuectl config set backoff_base 3  # This will fail!

# View all config
queuectl config show
```

## 📝 Assumptions & Trade-offs

### Assumptions
1. **Command Execution**: Jobs execute shell commands using `subprocess`
2. **Exit Codes**: Exit code 0 = success, non-zero = failure
3. **Timeouts**: Commands timeout after 5 minutes (configurable in code)
4. **Storage**: SQLite sufficient for medium-scale usage (<10K jobs/hour)
5. **Platform**: Cross-platform (Windows, Linux, macOS)

### Trade-offs
1. **SQLite vs. Redis/PostgreSQL**
   - ✅ Pro: Zero configuration, embedded, persistent
   - ⚠️ Con: Lower throughput than dedicated queue systems
   
2. **Polling vs. Push Notifications**
   - ✅ Pro: Simple implementation, no message broker needed
   - ⚠️ Con: 1-second delay when queue is empty
   
3. **Process-based vs. Thread-based Workers**
   - ✅ Pro: True parallelism, better isolation
   - ⚠️ Con: Higher memory overhead per worker

4. **File-based PID Tracking**
   - ✅ Pro: Simple, works across terminals
   - ⚠️ Con: Manual cleanup needed if process crashes

### Simplifications
- No job priorities (FIFO processing)
- No scheduled/delayed jobs (though retry provides delay)
- Basic command execution (no streaming output)
- Single database file (no sharding)

## 🌟 Bonus Features (Implemented)

- ✅ **Job timeout handling** (5-minute default)
- ✅ **Job output logging** (stdout/stderr captured)
- ✅ **Detailed job info command** (`queuectl info <job-id>`)
- ✅ **Cross-platform support** (Windows, Linux, macOS)
- ✅ **Graceful shutdown with SIGTERM handling**
- ✅ **Configuration persistence**
- ✅ **Comprehensive error messages**

## 🛠️ Development

### Project Structure
```
queuectl/
├── queuectl/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # CLI interface (Click)
│   ├── models.py            # Job and Config models
│   ├── storage.py           # SQLite persistence layer
│   ├── worker.py            # Worker process implementation
│   └── worker_manager.py    # Worker lifecycle management
├── test_queuectl.py         # Automated test suite
├── queuectl.py              # Entry point script
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup
└── README.md                # This file
```

### Running from Source
```bash
# After pip install -e .
queuectl <command>

# Check installation
queuectl --version
queuectl --help
```

## 🔑 Key Command Syntax Rules

### 1. **JSON Format is Required for Enqueue**
```bash
# ✅ CORRECT
queuectl enqueue '{"id":"job1","command":"echo Hello"}'

# ❌ WRONG - No --command flag exists
queuectl enqueue --command "echo Hello"
```

### 2. **Use Hyphens in Config Keys**
```bash
# ✅ CORRECT
queuectl config set max-retries 5

# ❌ WRONG
queuectl config set max_retries 5
```

### 3. **Worker Count Flag**
```bash
# ✅ CORRECT
queuectl worker start --count 3

# ❌ WRONG
queuectl worker start --workers 3
queuectl worker start -n 3
```

### 4. **Config Commands**
```bash
# ✅ Available commands
queuectl config show    # View all config
queuectl config set <key> <value>  # Set config

# ❌ NOT available
queuectl config get <key>   # Use 'show' instead
queuectl config list        # Use 'show' instead
```

## 🐛 Troubleshooting

### "Error: Invalid JSON format"
```bash
# Make sure to use single quotes for outer JSON
# Windows PowerShell:
queuectl enqueue '{"id":"job1","command":"echo Hello"}'

# Escape inner quotes properly
queuectl enqueue '{"id":"job1","command":"echo \"Hello World\""}'
```

### "Error: No such option: --workers"
```bash
# ❌ WRONG
queuectl worker start --workers 3

# ✅ CORRECT - Use --count
queuectl worker start --count 3
```

### "Error: Invalid config key"
```bash
# ❌ WRONG - Don't use underscores
queuectl config set max_retries 5

# ✅ CORRECT - Use hyphens
queuectl config set max-retries 5

# Valid keys are: max-retries, backoff-base, db-path
```

### Workers won't start
```bash
# Check if workers already running
queuectl worker status

# Force stop existing workers
queuectl worker stop

# Remove stale PID file if needed
# Windows: del queuectl_workers.pid
# Linux/Mac: rm queuectl_workers.pid
```

### Database locked errors
```bash
# Stop all workers first
python queuectl.py worker stop

# If issue persists, restart Python processes
# Database uses connection pooling with proper locking
```

### Jobs stuck in PROCESSING
```bash
# Usually means worker crashed mid-job
# Manual fix: Update job state directly or restart worker
# Prevention: Workers handle SIGTERM gracefully
```

## 📄 License

MIT License - see LICENSE file for details

## 👤 Author

**Your Name**
- GitHub: [[@akashrdj](https://github.com/yourusername)](https://github.com/akashrdj)
- Email: akashrj090@gmail.com

## 🙏 Acknowledgments

Built for the QueueCTL Backend Developer Internship Assignment.

---

## 📹 Demo Video

[Link to demo video showing QueueCTL in action]

*(Upload your demo video to Google Drive/YouTube and add link here)*

---

**Made with ❤️ using Python**
