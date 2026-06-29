# fastapi-template

[![CI](https://github.com/maksimzayats/fastapi-template/actions/workflows/lint_test.yaml/badge.svg?branch=main)](https://github.com/maksimzayats/fastapi-template/actions/workflows/lint_test.yaml)
[![Docs](https://img.shields.io/badge/docs-fastapi--template.zayats.dev-blue)](https://fastapi-template.zayats.dev)

A FastAPI project template with SQLAlchemy async repositories, Alembic migrations, dependency injection, JWT authentication, Redis-backed rate limiting, and strict quality checks.

## Quick Start

```bash
uv sync --locked --all-groups
cp .env.example .env
docker compose up -d postgres redis
make migrate
make dev
```

The API runs at `http://localhost:8000`. Health checks are available at `/api/v1/health`.

## What Is Included

- FastAPI delivery with full `/api/v1/...` route paths.
- SQLAlchemy async repositories, unit-of-work transactions, and Alembic migrations.
- User creation, JWT issue/refresh/revoke, current-user, staff-user lookup, and health endpoints.
- `diwire` dependency injection with explicit registrations for core contracts.
- Pydantic settings and DTO/schema boundaries.
- Docker Compose for PostgreSQL, PgBouncer, and Redis.
- Architecture, style, unit, and integration tests.

## Project Layout

- `src/fastapi_template/core/` - entities, DTOs, use cases, services, and contracts.
- `src/fastapi_template/infrastructure/` - SQLAlchemy, logging, telemetry, and throttling adapters.
- `src/fastapi_template/entrypoints/` - FastAPI app construction.
- `src/fastapi_template/ioc/` - dependency injection setup.
- `migrations/` - Alembic migration environment and versions.
- `management/` - maintenance scripts.
- `tests/` - unit, integration, architecture, and style tests.

## Commands

| Command | Purpose |
| --- | --- |
| `make dev` | Run the FastAPI development server |
| `make makemigrations` | Create an Alembic migration |
| `make migrate` | Apply Alembic migrations |
| `make check-migrations` | Check Alembic migration drift |
| `make test` | Run the test suite with a 100% coverage threshold |
| `make test-postgres` | Run SQLAlchemy integration tests against the required `INTEGRATION_DATABASE_URL` |
| `make lint` | Run Ruff, WPS/flake8, mypy, and repository checks |
| `make docs` | Serve documentation |

Read the full documentation at [fastapi-template.zayats.dev](https://fastapi-template.zayats.dev), or run `make docs`.
