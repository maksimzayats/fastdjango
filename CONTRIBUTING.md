# Contributing

This guide keeps the code-facing details for Modern Python Template: local
setup, commands, project layout, architecture expectations, and validation.

## Local Setup

Install dependencies:

```bash
uv sync --locked --all-groups
```

Create a local environment file:

```bash
cp .env.example .env
```

Start local dependencies:

```bash
docker compose up -d postgres redis
```

Apply database migrations:

```bash
make migrate
```

Run the API:

```bash
make dev
```

The API runs at `http://localhost:8000`. The health endpoint is
`GET /api/v1/health`.

## Project Layout

- `src/fastapi_template/core/` contains entities, DTOs, use cases, services,
  repository contracts, exceptions, and local business-module adapters.
- `src/fastapi_template/infrastructure/` contains shared SQLAlchemy wiring,
  logging, telemetry, throttling, and external technical adapters.
- `src/fastapi_template/entrypoints/` contains FastAPI app construction.
- `src/fastapi_template/ioc/` contains dependency injection setup.
- `migrations/` contains Alembic migration environment and versions.
- `management/` contains maintenance scripts.
- `tests/` contains unit, integration, architecture, and style tests.

## Architecture Rules

- Controllers parse HTTP requests, call use cases, and translate known
  application exceptions.
- Use cases expose one public method, `async def execute(...)`, and open the
  unit-of-work scope for workflows that need persistence.
- Services own focused reusable behavior and may receive an active `uow`, but
  they do not open transactions.
- Database access goes through repositories. Delivery tests and controllers do
  not import SQLAlchemy sessions, models, or concrete repositories.
- Source files stay scoped: one primary use case, controller, repository,
  SQLAlchemy model, DTO shape, entity, or service per file.
- Public HTTP routes are registered as full `/api/v1/...` paths.
- Public docstrings in `src/` and `management/` must explain contract,
  boundary behavior, domain meaning, side effects, or failure semantics.

## Commands

| Command | Purpose |
| --- | --- |
| `make dev` | Run the FastAPI development server |
| `make makemigrations` | Create an Alembic migration from model changes |
| `make migrate` | Apply Alembic migrations |
| `make check-migrations` | Fail when Alembic detects model changes without a migration |
| `make update-dependencies` | Sync dependency bounds and container image references |
| `make format` | Run formatting hooks |
| `make lint` | Run Ruff, WPS/flake8, mypy, and repository checks |
| `make test` | Run the test suite with a 100% coverage threshold |
| `make test-postgres` | Run repository and SQLAlchemy integration tests against PostgreSQL |
| `make docs` | Serve documentation locally |
| `make docs-build` | Build static documentation |

`make test-postgres` resets the target schema before running tests. Set
`INTEGRATION_DATABASE_URL` to a PostgreSQL database whose name starts with
`test_` or ends with `_test`.

## Validation

Run the full local gate before sending changes:

```bash
make format
make lint
make test
make docs-build
docker compose config
```

For faster focused checks, run the smallest relevant `uv run pytest ...`
command first, then run the full gate before finishing.

## Documentation

User-facing docs live under `docs/en/` and are built with MkDocs:

```bash
make docs
```

Keep the README focused on the template's benefits and public links. Put
developer setup, commands, architecture details, and validation workflow in
this file.
