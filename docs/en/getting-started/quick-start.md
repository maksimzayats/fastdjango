# Quick Start

Get the project running in minutes.

## Prerequisites

- Python 3.14+
- Docker and Docker Compose
- uv ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

## Step 1: Clone and Install Dependencies

```bash
git clone https://github.com/MaksimZayats/fastdjango.git
cd fastdjango

# Install all dependencies (including dev tools)
uv sync --locked --all-groups
```

## Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env
```

The default `.env` file is configured for local development. Key variables include:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `DJANGO_SECRET_KEY` | Development key | Django security key |
| `DJANGO_DEBUG` | `true` | Enable debug mode |

!!! warning "Production Configuration"
    For production, you must change `DJANGO_SECRET_KEY` and set `DJANGO_DEBUG=false`.

## Step 3: Start Infrastructure

Start the required services (PostgreSQL, Redis, MinIO):

```bash
docker compose up -d postgres redis minio minio-create-buckets
```

Verify services are running:

```bash
docker compose ps
```

You should see `postgres`, `redis`, and `minio` containers running.

## Step 4: Run Migrations

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

## Step 5: Start the Development Server

```bash
make dev
```

The FastAPI application is now available at:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Django Admin**: http://localhost:8000/django/admin/

## Step 6: Verify Installation

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
docker compose exec app python src/manage.py createsuperuser
```

Or use the shell directly:

```bash
uv run python src/manage.py createsuperuser
```

## Common Issues

### Port Already in Use

If port 8000 is occupied:

```bash
# Find the process
lsof -i :8000

# Or use a different port
uvicorn delivery.http.app:app --host 0.0.0.0 --port 8001
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
