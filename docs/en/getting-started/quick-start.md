# Quick Start

Get the project running in minutes.

## Prerequisites

- Python 3.14+
- uv ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- Docker and Docker Compose for local infrastructure choices

## Step 1: Create your repository and run setup

The cleanest flow is to create your own repository from the template on GitHub,
clone that new repository, and run:

```bash
make setup
```

The wizard detects your repository from `origin`, preserves Git history, and
only asks whether to commit the generated setup changes. Your `origin` already
points at your repository in this flow.

If you cloned the original template directly instead, run:

```bash
git clone https://github.com/maksimzayats/fastdjango.git && cd fastdjango && make setup
```

For a direct clone, let the wizard reinitialize Git so the generated project
does not keep the template history or `origin`.

The setup wizard renames the checkout folder to the project slug, renames the
project and Python package, writes `.env`, rewrites the app README, and lets you
choose database, Redis, storage, docs, public origins, Logfire defaults, and Git
setup for the flow you chose.

## Step 2: Install dependencies

```bash
# pyproject.toml / uv.lock
uv sync --locked --all-groups
```

## Step 3: Review environment

The generated `.env` file is configured for local development. Key variables include:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgres://...` or `sqlite:///...` | Database connection string |
| `REDIS_URL` | `redis://...` | Redis connection string |
| `DJANGO_SECRET_KEY` | Development key | Django security key |
| `DJANGO_DEBUG` | `true` | Enable debug mode |
| `STORAGE_BACKEND` | `local` or `s3` | File and static storage mode |
| `CORS_ALLOW_ORIGINS` | `["http://localhost"]` | Browser origins allowed to call the API |

!!! warning "Production Configuration"
    For production, you must change `DJANGO_SECRET_KEY` and set `DJANGO_DEBUG=false`.

## Step 4: Start infrastructure

Start the required local services for the choices you made in the wizard:

```bash
# docker/docker-compose.yaml
# If you selected local Docker PostgreSQL and local Docker Redis:
docker compose up -d postgres redis

# If you selected local MinIO storage:
docker compose up -d minio
docker compose up minio-create-buckets
```

Verify services are running:

```bash
# docker/docker-compose.yaml
docker compose ps
```

You can skip a local service when you selected SQLite, remote PostgreSQL,
remote Redis, local filesystem storage, or remote S3.

## Step 5: Run migrations

Apply database migrations to create the required tables:

```bash
# management/manage.py
# If you are using the Dockerized app services:
docker compose up migrations

# Or from the host:
make migrate
```

Collect static files for the admin panel:

```bash
# management/manage.py
# If you are using the Dockerized app services:
docker compose up collectstatic

# Or from the host:
make collectstatic
```

For Dockerized local MinIO, Compose overrides the internal endpoint for containers while `.env` keeps
the browser-reachable endpoint for host commands:

- `AWS_S3_ENDPOINT_URL=http://minio:9000` (internal container networking)
- `AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000` (browser-reachable static URLs)

## Step 6: Start the development server

```bash
# Makefile
make dev
```

The FastAPI application is now available at:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Django Admin**: http://localhost:8000/django/admin/

## Step 7: Verify installation

Check the health endpoint:

```bash
# src/fastdjango/entrypoints/fastapi/delivery/controllers/health.py
curl http://localhost:8000/v1/health
```

Expected response:

```json
{"status": "ok"}
```

## Optional: Start Celery workers

For background task processing:

```bash
# Makefile
# In a new terminal
make celery-dev

# For scheduled tasks (in another terminal)
make celery-beat-dev
```

## Optional: Create a superuser

To access Django Admin:

```bash
# management/manage.py
docker compose exec api python management/manage.py createsuperuser
```

Or use the shell directly:

```bash
# management/manage.py
uv run python management/manage.py createsuperuser
```

## Common issues

### Port already in use

If port 8000 is occupied:

```bash
# Terminal
# Find the process
lsof -i :8000

# Or use a different port
uv run uvicorn fastdjango.entrypoints.fastapi.app:app --host 0.0.0.0 --port 8001
```

### Database Connection Error

If you selected local Docker PostgreSQL, ensure it is running:

```bash
docker compose ps postgres
docker compose logs postgres
```

### Redis Connection Error

If you selected local Docker Redis, ensure it is running:

```bash
docker compose ps redis
docker compose logs redis
```

## Next Steps

- [Project Structure](project-structure.md) - Understand the codebase organization
- [Development Environment](development-environment.md) - Set up your IDE
- [Tutorial](../tutorial/index.md) - Learn by building a feature
