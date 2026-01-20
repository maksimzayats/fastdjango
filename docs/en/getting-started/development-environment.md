# Development Environment

This guide covers the tools and configuration for an optimal development experience.

## Code Quality Tools

The project uses multiple tools for code quality. All are configured in `pyproject.toml` and `ruff.toml`.

### Formatting: Ruff

[Ruff](https://docs.astral.sh/ruff/) handles code formatting and linting.

```bash
# Format code
make format

# Or directly
ruff format src tests
ruff check --fix src tests
```

### Type Checking

The project is configured for strict type checking. You can use any of the following type checkers:

| Tool | Command | Configuration |
|------|---------|---------------|
| **mypy** | `mypy src tests` | `mypy.ini` |
| **ty** | `ty check src tests` | Built-in |
| **pyrefly** | `pyrefly check src tests` | Built-in |

Why three type checkers? Different tools catch different issues. Use the one you prefer, but the CI pipeline uses `mypy --strict`.

```bash
# Run all linting tools
make lint
```

### Pre-commit Hooks

The project includes pre-commit hooks that run automatically before each commit:

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

Hooks include:

- Ruff formatting and linting
- Trailing whitespace removal
- YAML/TOML validation
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
    "mypy-type-checker.args": ["--config-file=mypy.ini"],
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
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOGGING_LEVEL=DEBUG

# Observability (optional)
LOGFIRE_ENABLED=false
```

### Test Environment

Tests use `.env.test` which is loaded automatically by pytest:

```bash
# tests/conftest.py loads .env.test
```

## Running the Application

### Development Servers

```bash
# FastAPI (HTTP API)
make dev
# Equivalent to: uvicorn delivery.http.app:app --reload --host 0.0.0.0 --port 8000

# Celery Worker
make celery-dev
# Equivalent to: celery -A delivery.tasks.app:celery_app worker --loglevel=info

# Celery Beat (Scheduler)
make celery-beat-dev
# Equivalent to: celery -A delivery.tasks.app:celery_app beat --loglevel=info
```

### Database Operations

```bash
# Create migrations
make makemigrations

# Apply migrations
make migrate

# Or using Django manage.py directly
uv run python src/manage.py makemigrations
uv run python src/manage.py migrate
```

## Testing

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/integration/http/v1/test_v1_users.py

# Run with verbose output
pytest -v tests/

# Run only unit tests
pytest tests/unit/

# Run with coverage report
pytest --cov=src --cov-report=html tests/
```

### Test Configuration

Tests require:

- PostgreSQL running (for integration tests)
- Redis running (for Celery tests)

The test fixtures automatically:

- Create isolated containers per test
- Roll back database transactions
- Clean up test data

## Debugging

### FastAPI Debug Mode

With `DJANGO_DEBUG=true`, the API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Logging

Set `LOGGING_LEVEL=DEBUG` for verbose logging:

```bash
LOGGING_LEVEL=DEBUG make dev
```

### Celery Debugging

For detailed Celery logs:

```bash
celery -A delivery.tasks.app:celery_app worker --loglevel=debug
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
