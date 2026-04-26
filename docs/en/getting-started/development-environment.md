# Development Environment

This guide covers the tools and configuration for an optimal development experience.

## Code Quality Tools

The project uses Ruff for formatting and linting, and mypy for strict type checking.
Ruff and mypy are configured in `pyproject.toml` and `ruff.toml`; Git hooks are
configured in `prek.toml`.

### Formatting: Ruff

Ruff handles code formatting and linting. It is installed in the project dev
environment for editor integration, and `prek` runs it through local hooks.

```bash
# Format code
make format
```

### Type Checking

The project is configured for strict type checking with mypy. It runs through
`prek` as part of the lint workflow:

| Tool | Command | Configuration |
|------|---------|---------------|
| **mypy** | `uv run prek run mypy --all-files` | `pyproject.toml`, `prek.toml` |

The mypy configuration enables the Django stubs plugin and the diwire plugin, so
framework settings and injected callables are checked with the same rules CI uses.

```bash
# Run all checks except tests
make lint
```

### Git Hooks

The project uses `prek` for local hooks. By default, `prek run` checks staged
files; `make lint` runs the same hooks across the whole repository.

```bash
# Install hooks
uv run prek install

# Check staged files
uv run prek run

# Check the whole repository
uv run prek run --all-files
```

Hooks include:

- Ruff formatting and linting
- mypy strict type checking
- Trailing whitespace removal
- YAML/TOML validation
- uv lockfile validation
- Large file detection

## IDE Configuration

### VS Code

Recommended extensions:

- **Python** (Microsoft)
- **Ruff** (Astral Software)
- **Mypy Type Checker** (Microsoft)

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": "explicit",
            "source.organizeImports": "explicit"
        }
    },
    "python.analysis.typeCheckingMode": "strict",
    "mypy-type-checker.args": [],
    "ruff.configurationPreference": "filesystemFirst"
}
```

### PyCharm

1. **Set interpreter**: Point to `.venv/bin/python`
2. **Enable Ruff**: Settings → Plugins → Install "Ruff"
3. **Configure mypy**: Settings → Tools → External Tools → Add mypy
4. **Mark source root**: Right-click `src/` → Mark Directory as → Sources Root

## Environment Variables

### Local Development

The `.env` file is loaded automatically. Copy from example:

```bash
cp .env.example .env
```

Key variables for development:

```bash
# Django
DJANGO_SECRET_KEY=development-secret-key-change-in-production
DJANGO_DEBUG=true

# Database
DATABASE_URL=postgres://postgres:example-postgres-password@localhost:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOGGING_LEVEL=DEBUG

# Observability (optional)
LOGFIRE_ENABLED=false
```

### Test Environment

Tests load `.env.test` automatically when it exists. If it does not, pytest falls
back to the committed `.env.test.example` defaults.

```bash
# tests/conftest.py loads .env.test, then falls back to .env.test.example
```

## Running the Application

### Development Servers

```bash
# FastAPI (HTTP API)
make dev
# Equivalent to: uv run uvicorn fastdjango.entrypoints.fastapi.app:app --reload --host 0.0.0.0 --port 8000

# Celery Worker
make celery-dev
# Equivalent to the watched Celery worker command in the Makefile

# Celery Beat (Scheduler)
make celery-beat-dev
# Equivalent to the watched Celery beat command in the Makefile
```

### Database Operations

```bash
# Create migrations
make makemigrations

# Apply migrations
make migrate

# Or using Django manage.py directly
uv run src/fastdjango/manage.py makemigrations
uv run src/fastdjango/manage.py migrate
```

## Testing

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/integration/fastapi/test_v1_users.py

# Run with verbose output
pytest -v tests/

# Run only unit tests
pytest tests/unit/

# Run with coverage report
pytest --cov=src --cov-report=html tests/
```

### Test Configuration

The default suite is self-contained: `.env.test.example` uses SQLite, and the
Celery test worker uses an in-memory broker/backend. Use PostgreSQL or Redis
only when you add project-specific integration tests that need those services.

The test fixtures automatically:

- Create isolated containers per test
- Roll back database transactions
- Clean up test data

## Debugging

### FastAPI Debug Mode

With `DJANGO_DEBUG=true`, the API documentation is available at:

- Swagger UI: http://localhost:8000/docs
ReDoc is disabled in this template; use Swagger UI for interactive API testing.

### Logging

Set `LOGGING_LEVEL=DEBUG` for verbose logging:

```bash
LOGGING_LEVEL=DEBUG make dev
```

### Celery Debugging

For detailed Celery logs:

```bash
uv run celery -A fastdjango.entrypoints.celery.app worker --loglevel=debug
```

## Docker Development

### Start All Services

```bash
# Infrastructure only
docker compose up -d postgres redis minio minio-create-buckets

# Run migrations
docker compose up migrations collectstatic

# Full stack (including app)
docker compose up -d
```

For Django admin static files in Docker, ensure `.env` includes both:

- `AWS_S3_ENDPOINT_URL=http://minio:9000` for app/container access.
- `AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000` for browser access.

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f postgres
```

### Reset Database

```bash
docker compose down -v  # Remove volumes
docker compose up -d postgres
docker compose up migrations
```

## Next Steps

- [Tutorial](../tutorial/index.md) - Learn by building a feature
- [Concepts](../concepts/index.md) - Understand the architecture
