# Spike Sorting Lab Hub

A spike sorting job management system built with Django + React. Allows researchers to submit spike sorting pipelines via JSON, track job progress in real-time, and manage job statuses.

## Tech Stack

- **Backend:** Django 5.2 + Django REST Framework
- **Frontend:** React 18 (built via `npm run build`, served by Django/WhiteNoise)
- **Database:** SQLite (path configurable via `DATABASE_PATH` env var)
- **Authentication:** Token-based (DRF)
- **Worker:** Python polling consumer (`qmodel_worker.py`)
- **Server:** Gunicorn with optional TLS (ports 9000 HTTP / 9443 HTTPS)
- **Deployment:** Docker (Ubuntu 24.04 base image)

## Key Features

- End-to-end job creation with atomic transactions
- SHA-256 configuration deduplication
- Pipeline dependency resolution
- Real-time status updates via React UI
- Admin interface for manual control
- FIFO queue with row-level database locking
- WhiteNoise static file serving (no Nginx required)
- Self-signed TLS via `deploy.sh`

---

## Deployment — Docker (Production)

### Prerequisites

- Docker + Docker Compose installed on the server
- NAS mounted at `/mnt/root_data_storage/`
- `DJANGO_SECRET_KEY` set in the shell environment

### Ports

The NAS itself uses 8000, 8080, and 8443. This container uses:

| Protocol | Host port | Container port |
|----------|-----------|----------------|
| HTTP     | 9000      | 9000           |
| HTTPS    | 9443      | 9443           |

### Bind-mount layout

| Host path | Container path | Access |
|-----------|---------------|--------|
| `/mnt/root_data_storage/users/sslh/trurnasdata` | `/data` | read-only (NAS database) |
| `/mnt/root_data_storage/users/sslh/persistentdata` | `/django_db` | read/write (Django DB + logs) |
| `/mnt/root_data_storage/experiments` | `/experiments` | read-only (binary recordings) |
| `./secrets` | `/app/secrets` | read-only (SSL certs) |

### Build and run

```bash
# Generate SSL certs into secrets/ (first time only)
./deploy.sh   # choose option 4 (setup only) to generate certs without starting a server

# Set the secret key
export DJANGO_SECRET_KEY="your-secret-key-here"

# Start the container
docker compose up -d

# View logs
docker compose logs -f
```

### Run migrations inside the container (first deploy)

```bash
docker compose exec spikesorting-labhub python manage.py migrate
docker compose exec spikesorting-labhub python manage.py createsuperuser
```

### Access

- HTTP:  `http://<server-ip>:9000/`
- HTTPS: `https://<server-ip>:9443/`
- Admin: `https://<server-ip>:9443/admin/`

---

## Local Development (without Docker)

### Prerequisites

- Python 3.13+
- Node.js 18+

### Quick setup via deploy.sh

```bash
./deploy.sh
# Follow prompts: creates venv, installs deps, runs migrations, generates certs, starts server
```

### Manual setup

```bash
# Backend
python3 -m venv .djangovenv
source .djangovenv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# Frontend (build React into Django's static root)
cd my-app
npm install
npm run build
cd ..

python manage.py collectstatic --noinput

# Run (HTTP)
gunicorn -c gunicorn.conf.py labhub.wsgi:application
# or
python manage.py runserver 0.0.0.0:9000

# Run (HTTPS)
gunicorn -c gunicorn.conf.py \
         --certfile=secrets/cert.crt \
         --keyfile=secrets/cert.key \
         -b 0.0.0.0:9443 \
         labhub.wsgi:application
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | insecure dev key | Must be set in production |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `DATABASE_PATH` | `Django_database/db.sqlite3` | Path to SQLite database file |
| `NAS_ROOT` | `experiments/` | Host path that replaces `$NAS$` in DB |
| `DATA_DIRS` | `experiments/,experiments/probes/` | Comma-separated dirs scanned for data files |

---

## Running the Worker

The worker polls the server for pending jobs and must be run in a separate terminal.

```bash
# Terminal 1 — server
source .djangovenv/bin/activate
gunicorn -c gunicorn.conf.py labhub.wsgi:application

# Terminal 2 — worker (HTTP)
source .djangovenv/bin/activate
python qmodel_worker.py

# Terminal 2 — worker (HTTPS, self-signed cert)
source .djangovenv/bin/activate
LABHUB_BASE_URL=https://localhost:9443 LABHUB_SSL_VERIFY=false python qmodel_worker.py
```

---

## API Reference

All endpoints require token authentication:

```
Authorization: Token YOUR_TOKEN_HERE
```

**Get Token:**
```bash
curl -X POST http://localhost:9000/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/submit-jobs/create-sorting-job/` | Create a new job |
| GET | `/submit-jobs/browse/` | Browse server-side data files |
| GET | `/job-queue/list/` | List all jobs (supports `status`, `limit`, `offset`) |
| GET | `/job-queue/<job_id>/` | Get job details and step statuses |
| GET | `/job-queue/statistics/` | Job count breakdown by status |
| GET | `/job-queue/all/` | Get all jobs (unfiltered) |
| POST | `/job-queue/cancel-job/` | Cancel a pending/running job |
| POST | `/job-queue/resume-job/` | Resume a canceled job |
| GET | `/job-queue/next-job/` | Worker: fetch next pending job |
| POST | `/job-queue/update-status/` | Worker: update job or step status |
| GET/POST | `/pipeline-factory/pipelines/` | List or create pipelines |
| GET/POST | `/pipeline-factory/pipeline-steps/` | List or create pipeline steps |

### Create Job Example

```bash
curl -X POST http://localhost:9000/submit-jobs/create-sorting-job/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recording": {
      "binfile": "/data/recording.bin",
      "sampling_rate": 30000,
      "num_channels": 32,
      "gain_to_uV": 0.195,
      "offset_to_uV": 0,
      "probe": "/data/probe.json"
    },
    "pipeline_id": 1,
    "environment": "local"
  }'
```

---

## Status Flow

```
Job:  pending -> fetched -> running -> completed
                                    -> failed
                                    -> canceled

Step: pending -> running -> completed
                          -> failed
```

---

## Project Structure

```
labhub/              # Django project settings, URLs, backends
job_queue/           # Job and step models, worker endpoints
pipeline_factory/    # Pipeline and step-config models
submit_jobs/         # Job creation API, serializers
my-app/              # React frontend source (build/ is served by Django)
  build/             # Compiled React app (committed or built on deploy)
gunicorn.conf.py     # Gunicorn config (binds 0.0.0.0:9000)
docker-compose.yml   # Production container with bind mounts
Dockerfile           # Ubuntu 24.04 image, Python 3.13, collectstatic
deploy.sh            # One-shot local setup + server start script
secrets/             # SSL certs (git-ignored, generated by deploy.sh)
```

---

## Running Tests

```bash
python manage.py test -v 2
```

---

## Admin Interface

`https://<host>:9443/admin/` — manually update job and step statuses, manage tokens.

---

## Common Issues

| Issue | Fix |
|-------|-----|
| Token invalid | Create new token via admin or `manage.py shell` |
| Job not processing | Check worker is running in a separate terminal |
| Step status not updating | Status choices are `completed` (steps) and `finished` (jobs) — not interchangeable |
| Port conflict | NAS uses 8000, 8080, 8443 — this app uses 9000 / 9443 |
| `collectstatic` fails at build | Ensure `my-app/build/` exists; run `npm run build` in `my-app/` first |
| Container can't write DB | Check `/mnt/root_data_storage/users/sslh/persistentdata` exists and is writable |
| `$NAS$` paths not resolving | Set `NAS_ROOT` env var to the worker's local mount path |
