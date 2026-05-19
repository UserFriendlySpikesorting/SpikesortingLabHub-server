# 📚 Spike Sorting Lab Hub - Complete Documentation

**Last Updated:** February 17, 2026  
**Status:** ✅ Complete & Production Ready

---

## 🗺️ Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Setup & Installation](#setup--installation)
4. [API Reference](#api-reference)
5. [Job Submission & Processing](#job-submission--processing)
6. [Web Interface](#web-interface)
7. [Status Management](#status-management)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 📖 Project Overview

### What is This?

A **spike sorting job management system** built with Django + React that allows researchers to:
- Submit spike sorting pipelines via JSON
- Track job progress in real-time
- Manage job statuses (pending → finished)
- Execute jobs with step-by-step processing

### Tech Stack

- **Backend:** Django 4.2.7 + Django REST Framework
- **Frontend:** React 18
- **Database:** SQLite/PostgreSQL with atomic transactions
- **Authentication:** Token-based (DRF)
- **Worker:** Python polling consumer

### Key Features

✅ End-to-end job creation with atomic transactions  
✅ SHA-256 configuration deduplication  
✅ Pipeline dependency resolution  
✅ Real-time status updates  
✅ Admin interface for manual control  
✅ React web UI for visualization  
✅ Worker polling for asynchronous processing  
✅ Row-level database locking for FIFO queue  

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    React Web App                         │
│              (Job Creation Wizard & Monitor)             │
└────────────┬────────────────────────────────┬───────────┘
             │                                │
      POST /jobs/create-sorting-job/   GET /jobs/list/
             │                                │
┌────────────▼────────────────────────────────▼───────────┐
│                  Django REST API                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Jobs App:                                           │ │
│  │ • create_sorting_job() - Job creation workflow    │ │
│  │ • list_jobs() - Paginated job listing             │ │
│  │ • get_job_status() - Status details               │ │
│  │ • job_statistics() - Stats breakdown              │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ QModel App (Pure Functions):                        │ │
│  │ • compute_fingerprint() - SHA-256 hashing          │ │
│  │ • get_or_create_step_configs() - Config dedup      │ │
│  │ • create_a_job() - Atomic job creation             │ │
│  │ • get_next_job_id() - FIFO queue with locking      │ │
│  │ • Worker endpoints for job fetching                │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────┬───────────┘
             │                                │
         Django ORM          GET /qmodel/getthenextjob/
             │                                │
┌────────────▼────────────────────────────────▼───────────┐
│                  PostgreSQL/SQLite                       │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ Job          │  │ JobStep       │  │ StepConfig   │ │
│  │ • job_id(PK) │  │ • identifier  │  │ • hash(PK)   │ │
│  │ • status     │  │ • job(FK)     │  │ • config     │ │
│  │ • env_config │  │ • function    │  │ • function   │ │
│  │ • created_at │  │ • depends_on  │  └──────────────┘ │
│  │              │  │ • status      │                    │
│  │              │  │ • config_hash │                    │
│  └──────────────┘  └───────────────┘                    │
└────────────────────────────────────────────────────────┘
             │
┌────────────▼─────────────────────────────────────────────┐
│              Python Worker (qmodel_worker.py)            │
│                                                          │
│  1. Polls: GET /qmodel/getthenextjob/                   │
│  2. Receives: job_data with steps & configs             │
│  3. Processes: Each step in dependency order            │
│  4. Updates: POST status after each step                │
│  5. Completes: Marks job as finished                    │
└──────────────────────────────────────────────────────────┘
```

### Data Flow: Job Submission

```
Step 1: React Wizard Submission
  Input: {recording, pipeline_id, environment}
           ↓
Step 2: Validate Request
  CreateSortingJobSerializer validates all fields
           ↓
Step 3: Create Recording Config
  get_or_create_step_configs("recording", recording_data)
  Returns: recording_identifier (SHA-256 hash)
           ↓
Step 4: Load Pipeline Steps
  PipelineStep.objects.filter(pipeline_id=pipeline_id)
           ↓
Step 5: Build Job Steps
  For each pipeline step:
    • Get real config_block_hash from StepConfig
    • Store in JobStep with FK reference
           ↓
Step 6: Resolve Dependencies
  Convert placeholder IDs → real config_block_hash values
           ↓
Step 7: Create Job Environment
  Build job_env_config (base_directory, log_level, etc.)
           ↓
Step 8: Atomic Job Creation
  create_a_job(job_env_config, job_steps_data)
    → Creates Job record
    → Creates all JobSteps in one transaction
    → Returns job object
           ↓
Result: Job stored in database with status=pending
```

### Status Flow

**Job Status:**
```
pending → fetched → running → finished
  ↓
  └─ failed (at any point)
```

**Step Status:**
```
pending → running → completed
  ↓
  └─ failed (at any point)
```

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.8+
- PostgreSQL or SQLite
- Node.js 14+ (for React)
- pip & npm

### Installation

```bash
# Clone repository
git clone <repo-url>
cd spikesorting-labhub-try-error

# Backend Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database Setup
python manage.py migrate

# Create Superuser
python manage.py createsuperuser

# Frontend Setup
cd my-app
npm install
npm run build
cd ..

# Run Server
python manage.py runserver
```

### Configuration

**Django Settings (`labhub/settings.py`):**
- `ALLOWED_HOSTS`: Add your domain
- `DATABASES`: Configure database connection
- `STATIC_URL`: Static files path
- `CORS_ALLOWED_ORIGINS`: Allow frontend origin

**Environment Variables:**
```bash
DEBUG=False  # Production
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://...
```

---

## 📡 API Reference

### Authentication

All endpoints require token authentication:

```bash
Authorization: Token YOUR_TOKEN_HERE
```

**Get Token:**
```bash
curl -X POST http://localhost:8000/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

### Job Creation

**Endpoint:** `POST /jobs/create-sorting-job/`

**Request:**
```json
{
  "recording": {
    "binfile": "/path/to/recording.bin",
    "sampling_rate": 30000,
    "num_channels": 32,
    "gain": 0.195,
    "offset": 0,
    "probe": "/path/to/probe.json"
  },
  "pipeline_id": 1,
  "environment": "local"
}
```

**Response:**
```json
{
  "message": "Job created successfully",
  "job_id": "e421aa14-e909-411c-9162-41932c836c26",
  "recording_identifier": "960b137a244a8765...",
  "pipeline_steps_count": 5,
  "job_steps_count": 6,
  "status": "pending"
}
```

### Job Listing

**Endpoint:** `GET /jobs/list/`

**Query Parameters:**
- `status`: Filter by status (pending, fetched, running, finished, failed)
- `limit`: Results per page (default: 100)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "total_count": 25,
  "count": 10,
  "limit": 10,
  "offset": 0,
  "jobs": [
    {
      "job_id": "e421aa14-e909-411c...",
      "status": "pending",
      "created_at": "2026-02-17T10:30:00Z",
      "completed_steps": 0,
      "step_count": 6,
      "job_steps": [...]
    }
  ]
}
```

### Job Status

**Endpoint:** `GET /jobs/status/<job_id>/`

**Response:**
```json
{
  "job_id": "e421aa14-e909-411c...",
  "status": "running",
  "job_env": {...},
  "job_steps": [
    {
      "identifier": "abc123...",
      "function": "recording",
      "status": "completed",
      "depends_on": []
    }
  ]
}
```

### Job Statistics

**Endpoint:** `GET /jobs/statistics/`

**Response:**
```json
{
  "total_jobs": 25,
  "status_breakdown": {
    "pending": 5,
    "fetched": 2,
    "running": 3,
    "finished": 14,
    "failed": 1
  }
}
```

### Worker: Get Next Job

**Endpoint:** `GET /qmodel/getthenextjob/`

**Response:**
```json
{
  "version": "0.4.1",
  "si": "0.101.0",
  "job_id": "e421aa14-e909-411c...",
  "job_evn": {...},
  "job_steps": [
    {
      "function": "recording",
      "identifier": "960b137a244a...",
      "depends": []
    }
  ],
  "identifier_hash": {
    "960b137a244a...": {...config...},
    "4c746a61586a...": {...config...}
  }
}
```

### Worker: Update Status

**Endpoint:** `POST /qmodel/getthenextjob/`

**Update Job Status:**
```json
{
  "job_id": "e421aa14-e909-411c...",
  "status": "running"
}
```

**Update Step Status:**
```json
{
  "job_id": "e421aa14-e909-411c...",
  "step_id": "960b137a244a...",
  "status": "completed"
}
```

---

## 💼 Job Submission & Processing

### Complete Job Submission Example

```python
import json
import requests

TOKEN = "your-token-here"
HEADERS = {"Authorization": f"Token {TOKEN}"}

job_payload = {
    "recording": {
        "binfile": "/data/mouse1_session1.bin",
        "sampling_rate": 30000,
        "num_channels": 32,
        "gain": 0.195,
        "offset": 0,
        "probe": "/data/probes/cambridge32.json"
    },
    "pipeline_id": 1,
    "environment": "local"
}

response = requests.post(
    "http://localhost:8000/jobs/create-sorting-job/",
    json=job_payload,
    headers=HEADERS
)

if response.status_code == 201:
    job_data = response.json()
    print(f"Job created: {job_data['job_id']}")
else:
    print(f"Error: {response.json()}")
```

### Job Processing Workflow

**1. Submission (React)**
- User fills job wizard
- POST to `/jobs/create-sorting-job/`
- Job created with status=pending

**2. Queue (Database)**
- Job waits in pending queue
- Ordered by created_at (FIFO)
- Row-level lock prevents duplicate fetches

**3. Worker Fetch**
- Worker calls GET `/qmodel/getthenextjob/`
- Database returns oldest pending job
- Job status changed to fetched

**4. Processing**
- Worker receives job_data with all steps
- Processes each step in dependency order
- Respects depends_on array

**5. Status Update**
- After each step completes
- Worker POSTs to update step status
- Status: pending → running → completed

**6. Completion**
- When all steps complete
- Worker updates job status to finished
- Job removed from processing queue

---

## 🎨 Web Interface

### React Components

**ManageJobs.js** - Main job management interface

Features:
- Job listing with filtering
- Real-time status updates
- Job detail view with steps
- Status update buttons
- Progress tracking
- Step dependency visualization

**Job Card Display:**
```
┌─────────────────────────────┐
│ e421aa14-e909-411c (PENDING)│
├─────────────────────────────┤
│ Created: Feb 17, 10:30 AM  │
│ Environment: local         │
│                             │
│ Progress: 0/6 steps        │
│ ▪░░░░░░░░░░░░░░░░░░░░░░░░  0%
│                             │
│ [View Details →]            │
└─────────────────────────────┘
```

**Job Details View:**
```
Job Details: e421aa14-e909-411c

Job Information
━━━━━━━━━━━━━━
Job ID: e421aa14-e909-411c-9162-41932c836c26
Status: ⟳ RUNNING
Created: Feb 17, 2026 10:30 AM
Progress: 2/6 steps completed

[Pending] [Fetched] [Running] [Finished] [Failed]

Environment
━━━━━━━━━━━━━━
Environment: local
Base Directory: /data/recordings/
Log Level: DEBUG

Job Steps
━━━━━━━━━━━━━━
1. recording (✓) [⋯] [⟳] [✓] [✗]
2. preprocessing (⟳) [⋯] [⟳] [✓] [✗]
3. sorting (⋯) [⋯] [⟳] [✓] [✗]
```

---

## 🎛️ Status Management

### Three Ways to Update Status

### 1. Django Admin

**URL:** `http://localhost:8000/admin/`

**For Jobs:**
- Navigate to QMODEL → Jobs
- Select jobs (checkboxes)
- Action: "Mark selected as Running" (or other status)
- Click "Go"

**For Steps:**
- Navigate to QMODEL → Job steps
- Select steps
- Action: "Mark selected steps as Completed"
- Click "Go"

### 2. React Web UI

**URL:** `http://localhost:8000/`

**For Jobs:**
1. Manage Jobs → Click job card
2. Status section: Click desired button
3. Updates instantly

**For Steps:**
1. Job details view
2. Each step has 4 circular buttons
3. Click to update individual step

### 3. API/cURL

**Update Job:**
```bash
curl -X POST http://localhost:8000/qmodel/getthenextjob/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "...", "status": "running"}'
```

**Update Step:**
```bash
curl -X POST http://localhost:8000/qmodel/getthenextjob/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "...", "step_id": "...", "status": "completed"}'
```

---

## 🧪 Testing

### Running Tests

```bash
# All tests
python manage.py test qmodel -v 2

# Specific test class
python manage.py test qmodel.tests.TestComputeFingerprint -v 2

# With coverage
coverage run --source='qmodel' manage.py test qmodel
coverage report
```

### Test Coverage

38+ comprehensive tests covering:
- Pure functions (fingerprinting, deduplication)
- Model creation and validation
- Job creation workflow
- Status transitions
- Error handling
- Edge cases

### Key Tests

| Test | Purpose |
|------|---------|
| `TestComputeFingerprint` | Verify SHA-256 hashing consistency |
| `TestGetOrCreateStepConfigs` | Deduplication logic |
| `TestCreateAJob` | Atomic job creation |
| `TestGetNextJobId` | FIFO queue ordering |
| `TestCreateSortingJobAPI` | End-to-end API workflow |

---

## 🚀 Deployment

### Pre-Deployment Checklist

```bash
# Verify configuration
python manage.py check

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic --noinput

# Check database migrations
python manage.py showmigrations
```

### Production Settings

**settings.py:**
```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECRET_KEY = os.environ.get('SECRET_KEY')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Deployment Options

**Option 1: Simple Deploy Script**
```bash
bash simple_deploy.sh
```

**Option 2: GitHub Actions**
```bash
bash github_deploy.sh
```

**Option 3: Manual Deployment**
```bash
# SSH to server
ssh user@server

# Pull latest code
git pull origin main

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart service
sudo systemctl restart django
```

---

## 🔧 Troubleshooting

### Common Issues

**Issue: Job status not updating**
- Solution: Verify JobStep status choices (completed, not finished)
- Check: Update status choices in model
- Test: Use Django admin to verify changes

**Issue: Dependencies not resolving**
- Solution: Check `depends_on` contains actual config_block_hash values
- Debug: Query database directly
  ```bash
  python manage.py shell
  >>> from qmodel.models import PipelineStep
  >>> step = PipelineStep.objects.first()
  >>> print(step.depends_on)
  ```

**Issue: Worker not picking up jobs**
- Solution: Verify worker has valid token
- Check: Worker is pointing to correct endpoint
- Test: Run worker in foreground for debugging

**Issue: Authentication token invalid**
- Solution: Create new token
  ```bash
  python manage.py shell
  >>> from rest_framework.authtoken.models import Token
  >>> Token.objects.all().delete()
  >>> token = Token.objects.create(user=User.objects.first())
  ```

**Issue: Database locked**
- Solution: Check for long-running transactions
- Restart: May need to restart worker process

**Issue: Deduplication not working**
- Solution: Verify config hashing is deterministic
- Check: `compute_fingerprint()` uses `sort_keys=True`
- Test: Hash same config twice, should match

### Debug Commands

```bash
# Check job queue
python manage.py shell
>>> from qmodel.models import Job
>>> Job.objects.filter(status='pending').count()

# View job details
>>> job = Job.objects.get(job_id='...')
>>> print(job.jobstep_set.all())

# Check step configs
>>> from qmodel.models import StepConfig
>>> StepConfig.objects.count()
>>> list(StepConfig.objects.values('function').distinct())

# Verify token
>>> from rest_framework.authtoken.models import Token
>>> Token.objects.all()
```

### Logs

**Django Logs:**
```bash
tail -f logs/django.log
```

**Worker Logs:**
```bash
python qmodel_worker.py  # Run in foreground to see output
```

---

## 📊 Database Schema

### Job

| Field | Type | Notes |
|-------|------|-------|
| job_id | UUID | Primary key |
| status | CharField | pending/fetched/running/finished/failed |
| job_env_config | JSONField | Environment configuration |
| created_at | DateTime | Auto-set on creation |

### JobStep

| Field | Type | Notes |
|-------|------|-------|
| identifier | CharField | Step unique ID within job |
| job | ForeignKey | Links to Job |
| function | CharField | Step function name |
| status | CharField | pending/running/completed/failed |
| depends_on | JSONField | Array of dependency hashes |
| config_block_hash | ForeignKey | Links to StepConfig |

### StepConfig

| Field | Type | Notes |
|-------|------|-------|
| config_block_hash | CharField | Primary key (SHA-256) |
| config_block | JSONField | Actual configuration |
| function | CharField | Function name |

### Pipeline

| Field | Type | Notes |
|-------|------|-------|
| pipeline_id | AutoField | Primary key |
| description | TextField | Pipeline description |
| created_at | DateTime | Auto-set on creation |

### PipelineStep

| Field | Type | Notes |
|-------|------|-------|
| pipeline | ForeignKey | Links to Pipeline |
| pipeline_step_id | AutoField | Primary key |
| config_block_hash | ForeignKey | Links to StepConfig |
| depends_on | JSONField | Real config_block_hash dependencies |

---

## 📝 Key Code Files

### Models (`qmodel/models.py`)

**Pure Functions:**
- `compute_fingerprint()` - SHA-256 config hashing
- `get_or_create_step_configs()` - Config deduplication
- `create_a_job()` - Atomic job creation
- `get_next_job_id()` - FIFO queue with locking

**Model Classes:**
- `Job` - Main job record
- `JobStep` - Individual step in job
- `StepConfig` - Unique config storage

### Views (`qmodel/views.py`)

**Worker Endpoints:**
- `get_job()` - Fetch next job
- `update_job_status()` - Update status
- `next_job_get_logic()` - GET handler
- `next_job_post_logic()` - POST handler

### Serializers (`jobs/serializers.py`)

**Validation:**
- `CreateSortingJobSerializer` - Full job creation validation
- Input validation for all fields
- Dependency resolution

### Admin (`qmodel/admin.py`)

**Admin Actions:**
- JobAdmin: Mark as pending/fetched/running/finished/failed
- JobStepAdmin: Mark as pending/running/completed/failed

---

## 🎯 Quick Reference

### Most Common Commands

```bash
# Start server
python manage.py runserver

# Create job via API
curl -X POST http://localhost:8000/jobs/create-sorting-job/ \
  -H "Authorization: Token TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_job.json

# List jobs
curl http://localhost:8000/jobs/list/ \
  -H "Authorization: Token TOKEN"

# Run tests
python manage.py test qmodel -v 2

# Access admin
http://localhost:8000/admin/

# Access web UI
http://localhost:8000/
```

### Most Common Issues

| Issue | Solution |
|-------|----------|
| Token invalid | Create new token in admin or shell |
| Job not processing | Check worker is running |
| Status not updating | Verify status choices in model |
| Dependencies broken | Check `depends_on` has real hashes |
| Deduplication failed | Check config hashing logic |

---

## ✅ Checklist

**Before Going Live:**
- [ ] Run all tests (`python manage.py test`)
- [ ] Check deployment settings (`DEBUG = False`)
- [ ] Configure database
- [ ] Set SECRET_KEY in environment
- [ ] Collect static files
- [ ] Test job submission end-to-end
- [ ] Verify worker processing
- [ ] Test status updates
- [ ] Set up monitoring/logging
- [ ] Document custom configurations

---

## 📞 Support

**For Issues:**
1. Check Troubleshooting section above
2. Run debug commands to inspect state
3. Review logs
4. Check test files for usage examples
5. Refer to API Reference

**Common Scenarios:**
- **New to the project?** Start with Architecture section
- **Need to submit a job?** See Job Submission section
- **Want to deploy?** See Deployment section
- **Something broken?** See Troubleshooting section

---

**Version:** 2.0  
**Last Updated:** February 17, 2026  
**Status:** ✅ Production Ready
