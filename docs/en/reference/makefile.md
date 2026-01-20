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
| `make format` | Format code with ruff |
| `make lint` | Run all linters (ruff, ty, pyrefly, mypy) |
| `make test` | Run tests with coverage |

### Examples

```bash
# Before committing
make format
make lint

# Run tests
make test
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
uvicorn delivery.http.app:app --reload --host 0.0.0.0 --port 8000
```

- Hot reloading enabled
- Accessible at http://localhost:8000
- API docs at http://localhost:8000/docs

### `make celery-dev`

Runs:
```bash
celery -A delivery.tasks.app:celery_app worker --loglevel=info
```

- Processes background tasks
- Requires Redis running
- Logs to console

### `make celery-beat-dev`

Runs:
```bash
celery -A delivery.tasks.app:celery_app beat --loglevel=info
```

- Schedules periodic tasks
- Requires Redis running
- Must run alongside worker

### `make format`

Runs:
```bash
ruff format src tests
ruff check --fix src tests
```

- Formats Python files
- Auto-fixes lint issues where possible

### `make lint`

Runs multiple type checkers:
```bash
ruff check src tests
ty check src tests
pyrefly check src tests
mypy src tests
```

- All must pass for CI
- `mypy --strict` is the primary checker

### `make test`

Runs:
```bash
pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

- Requires 80%+ code coverage
- Generates coverage report
- Fails if coverage is below threshold

### `make migrate`

Runs:
```bash
uv run python src/manage.py migrate
```

- Applies all pending migrations
- Requires database running

### `make makemigrations`

Runs:
```bash
uv run python src/manage.py makemigrations
```

- Detects model changes
- Creates migration files in `migrations/` directories

### `make docs`

Runs:
```bash
mkdocs serve -f docs/mkdocs.yml
```

- Serves docs at http://localhost:8000
- Live reload on file changes

### `make docs-build`

Runs:
```bash
mkdocs build -f docs/mkdocs.yml
```

- Builds static HTML to `docs/site/`
- Validates all links

## Common Workflows

### Starting Fresh

```bash
# Install dependencies
uv sync --locked --all-groups

# Copy environment
cp .env.example .env

# Start infrastructure
docker compose up -d postgres redis minio minio-create-buckets

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

Ensure PostgreSQL is running:

```bash
docker compose up -d postgres
```

### Redis Connection Error

Ensure Redis is running:

```bash
docker compose up -d redis
```
