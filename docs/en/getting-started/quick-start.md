# Quick Start

Get the project running in minutes.

## Prerequisites

- Python 3.14+
- Docker and Docker Compose
- uv ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

## Step 1: Clone and Run Setup

```bash
git clone https://github.com/MaksimZayats/fastdjango.git
cd fastdjango
make setup
```

The setup wizard renames the template, writes `.env`, rewrites the app README, and lets you choose database,
Redis, storage, docs, public origins, and Logfire defaults.

## Step 2: Install Dependencies

```bash
# Install all dependencies (including dev tools)
uv sync --locked --all-groups
```

## Step 3: Review Environment

The generated `.env` file is configured for local development. Key variables include:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgres://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://...` | Redis connection string |
| `DJANGO_SECRET_KEY` | Development key | Django security key |
| `DJANGO_DEBUG` | `true` | Enable debug mode |
| `STORAGE_BACKEND` | `local` or `s3` | File and static storage mode |
| `CORS_ALLOW_ORIGINS` | `["http://localhost"]` | Browser origins allowed to call the API |

!!! warning "Production Configuration"
    For production, you must change `DJANGO_SECRET_KEY` and set `DJANGO_DEBUG=false`.

## Step 4: Start Infrastructure

Start the required local services for the choices you made in the wizard:

```bash
# If you selected local Docker PostgreSQL and local Docker Redis:
docker compose up -d postgres redis

# If you selected local MinIO storage:
docker compose up -d minio
docker compose up minio-create-buckets
```

Verify services are running:

```bash
docker compose ps
```

You can skip a local service when you selected SQLite, remote PostgreSQL, remote Redis, or remote S3.

## Step 5: Run Migrations

Apply database migrations to create the required tables:

```bash
# Using Docker (recommended)
docker compose up migrations

# Or manually
make migrate
```

Collect static files for the admin panel:

```bash
docker compose up collectstatic
```

For Dockerized local MinIO, Compose overrides the internal endpoint for containers while `.env` keeps
the browser-reachable endpoint for host commands:

- `AWS_S3_ENDPOINT_URL=http://minio:9000` (internal container networking)
- `AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000` (browser-reachable static URLs)

## Step 6: Start the Development Server

```bash
make dev
```

The FastAPI application is now available at:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Django Admin**: http://localhost:8000/django/admin/

## Step 7: Verify Installation

Check the health endpoint:

```bash
curl http://localhost:8000/v1/health
```

Expected response:

```json
{"status": "ok"}
```

## Optional: Start Celery Workers

For background task processing:

```bash
# In a new terminal
make celery-dev

# For scheduled tasks (in another terminal)
make celery-beat-dev
```

## Optional: Create a Superuser

To access Django Admin:

```bash
docker compose exec api python management/manage.py createsuperuser
```

Or use the shell directly:

```bash
uv run python management/manage.py createsuperuser
```

## Common Issues

### Port Already in Use

If port 8000 is occupied:

```bash
# Find the process
lsof -i :8000

# Or use a different port
uv run uvicorn fastdjango.entrypoints.fastapi.app:app --host 0.0.0.0 --port 8001
```

### Database Connection Error

Ensure PostgreSQL is running:

```bash
docker compose ps postgres
docker compose logs postgres
```

### Redis Connection Error

Ensure Redis is running:

```bash
docker compose ps redis
docker compose logs redis
```

## Next Steps

- [Project Structure](project-structure.md) - Understand the codebase organization
- [Development Environment](development-environment.md) - Set up your IDE
- [Tutorial](../tutorial/index.md) - Learn by building a feature
