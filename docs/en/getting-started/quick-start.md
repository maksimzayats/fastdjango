# Quick Start

Get the project running in minutes.

## Prerequisites

- Python 3.14+
- uv ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- Docker and Docker Compose for local infrastructure choices

## Step 1: Create an empty repository

Create an empty repository on GitHub for your generated project, then clone it.
Your `origin` should point at your project repository, not at
modern-python-template.

```bash
git clone https://github.com/[org]/[repo].git
cd [repo]
```

The edited prompt will point the agent at
`https://github.com/maksimzayats/modern-python-template` as the source template.

## Step 2: Customize the prompt template

Copy the prompt from
[`PROMPT_TEMPLATE.md`](https://github.com/maksimzayats/modern-python-template/blob/main/PROMPT_TEMPLATE.md).
Set the project name, update any optional bracketed values, then remove any
removable capability bullets you do not want. By default, the agent derives
package, distribution, Docker, docs, and display names from the project name;
you can override those derived names in natural language.

Keep the modern-python-template Base intact. FastAPI delivery, Django ORM and
admin, dependency injection, architecture guardrails, tests, linting, and typing
are mandatory for every generated project.

## Step 3: Run agent-led setup

Open your empty project repository in an LLM coding agent and paste the edited
prompt. The agent should bring in the template source, preserve your project
repo's Git history and `origin`, rename the project and Python package, write
`.env`, update the app README, remove omitted capabilities, refresh the
lockfile, and run checks.

Review the resulting diff and `.env` before starting the application. If the
generated project keeps a capability, its code, tests, dependencies, settings,
environment variables, Docker services, and docs should all be present. If it
does not keep a capability, those pieces should be gone.

## Step 4: Install dependencies

```bash
# pyproject.toml / uv.lock
uv sync --locked --all-groups
```

## Step 5: Review environment

The generated `.env` file should be configured for local development. Key
variables usually include:

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

## Step 6: Start infrastructure

Start the required local services for the capabilities kept in your prompt:

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

You can skip a local service when the generated project keeps SQLite, remote
PostgreSQL, remote Redis, local filesystem storage, or remote S3.

## Step 7: Run migrations

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

## Step 8: Start the development server

```bash
# Makefile
make dev
```

The FastAPI application is now available at:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Django Admin**: http://localhost:8000/django/admin/

## Step 9: Verify installation

Check the health endpoint:

```bash
# src/modern_python_template/core/health/delivery/fastapi/controllers.py
curl http://localhost:8000/v1/health
```

Expected response:

```json
{"status": "ok"}
```

## Optional: Start Celery workers

If your generated project keeps Celery, start background task processing:

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
uv run uvicorn modern_python_template.entrypoints.fastapi.app:app --host 0.0.0.0 --port 8001
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
