# Makefile Commands

Quick reference for all development commands.

## Development

| Command | Description |
|---------|-------------|
| `make dev` | Start FastAPI development server with hot reload |
| `make celery-dev` | Start Celery worker for background tasks |
| `make celery-beat-dev` | Start Celery beat scheduler |

### Examples

```bash
# Start the API server
make dev

# In another terminal, start Celery
make celery-dev

# For scheduled tasks
make celery-beat-dev
```

## Database

| Command | Description |
|---------|-------------|
| `make migrate` | Apply database migrations |
| `make makemigrations` | Create new migrations from model changes |

### Examples

```bash
# After modifying models
make makemigrations

# Apply changes to database
make migrate
```

## Code Quality

| Command | Description |
|---------|-------------|
| `make format` | Format code through prek hooks |
| `make lint` | Run all prek checks except tests |
| `make test` | Run tests with coverage |
| `make update-dependencies` | Update uv lock, dependency bounds, CI pins, and container image pins |

### Examples

```bash
# Before committing
make format
make lint

# Run tests
make test

# Update dependency bounds and CI action pins
make update-dependencies
```

## Documentation

| Command | Description |
|---------|-------------|
| `make docs` | Serve documentation with live reload |
| `make docs-build` | Build static documentation |

### Examples

```bash
# Preview documentation locally
make docs

# Build for deployment
make docs-build
```

## Command Details

### `make dev`

Runs:
```bash
uv run uvicorn modern_python_template.entrypoints.fastapi.app:app --reload --host 0.0.0.0 --port 8000
```

- Hot reloading enabled
- Accessible at http://localhost:8000
- API docs at http://localhost:8000/docs

### `make update-dependencies`

Runs:
```bash
uv run python -m management.dependency_updater $(ARGS)
```

- Runs `uv lock --upgrade`
- Syncs direct dependency lower bounds in `pyproject.toml` from `uv.lock`
- Updates GitHub Action pins and supported CI tool versions in `.github/workflows`
- Updates Dockerfile and Docker Compose image pins, including matching docs references
- Runs `uv lock` again after pyproject changes
- Prints progress while it checks package indexes, GitHub, and container registries

Preview without writing files:
```bash
make update-dependencies ARGS="--dry-run"
```

Hide progress messages:
```bash
make update-dependencies ARGS="--quiet"
```

### `make celery-dev`

Runs:
```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run watchmedo auto-restart \
    --directory=src \
    --pattern='*.py' \
    --recursive \
    -- celery -A modern_python_template.entrypoints.celery.app worker --loglevel=DEBUG
```

- Processes background tasks
- Requires Redis to be configured and reachable
- Logs to console

### `make celery-beat-dev`

Runs:
```bash
uv run watchmedo auto-restart \
    --directory=src \
    --pattern='*.py' \
    --recursive \
    -- celery -A modern_python_template.entrypoints.celery.app beat --loglevel=DEBUG
```

- Schedules periodic tasks
- Requires Redis to be configured and reachable
- Must run alongside worker

### `make format`

Runs:
```bash
uv run prek run trailing-whitespace end-of-file-fixer ruff-check-fix ruff-format-fix --all-files --hook-stage manual
```

- Formats Python files through local Ruff hooks
- Fixes Ruff lint issues where possible
- Normalizes trailing whitespace and final newlines

### `make lint`

Runs code quality checks:
```bash
uv run prek run --all-files
```

- Runs the full repository, matching CI
- Use `uv run prek run` to check only staged files
- `mypy --strict` is the only type checker

### `make test`

Runs:
```bash
uv run --all-groups pytest tests/
```

- Requires 80%+ code coverage
- Generates an HTML coverage report in `htmlcov/`
- Fails if coverage is below threshold

### `make migrate`

Runs:
```bash
uv run python management/manage.py migrate
```

- Applies all pending migrations
- Requires database running

### `make makemigrations`

Runs:
```bash
uv run python management/manage.py makemigrations
```

- Detects model changes
- Creates migration files in `migrations/` directories

### `make docs`

Runs:
```bash
uv run mkdocs serve --livereload -f docs/mkdocs.yml
```

- Serves docs at http://localhost:8000
- Live reload on file changes

### `make docs-build`

Runs:
```bash
uv run mkdocs build -f docs/mkdocs.yml
```

- Builds static HTML to `site/`
- Validates all links

## Common Workflows

### Starting Fresh

```bash
# First create the generated project with PROMPT_TEMPLATE.md and an LLM agent.

# Install dependencies
uv sync --locked --all-groups

# Start local infrastructure for the capabilities kept in the generated project
docker compose up -d postgres redis

# If you selected local MinIO storage
docker compose up -d minio
docker compose up minio-create-buckets

# Run migrations
make migrate

# Start server
make dev
```

### Before Committing

```bash
make format
make lint
make test
```

### Working with Celery

```bash
# Terminal 1: API
make dev

# Terminal 2: Worker
make celery-dev

# Terminal 3: Scheduler (if needed)
make celery-beat-dev
```

### Creating a New Feature

```bash
# Create models and services
# Then:
make makemigrations
make migrate

# Run tests
make test
```

## Troubleshooting

### Command Not Found

Ensure you have `make` installed:

```bash
# macOS
xcode-select --install

# Ubuntu/Debian
apt-get install build-essential
```

### Permission Denied

If using Docker:

```bash
sudo make <command>
# Or fix Docker permissions
```

### Database Connection Error

If you selected local Docker PostgreSQL, ensure it is running:

```bash
docker compose up -d postgres
```

### Redis Connection Error

If you selected local Docker Redis, ensure it is running:

```bash
docker compose up -d redis
```
