# FastAPI Template

FastAPI Template is a Python 3.14 application template for building API services with clean application boundaries.

It includes:

- FastAPI HTTP delivery with full `/api/v1/...` route paths.
- SQLAlchemy async persistence and Alembic migrations.
- `diwire` dependency injection.
- Pydantic settings backed by environment variables.
- JWT authentication, refresh-token rotation, user endpoints, health checks, and Redis-backed rate limiting.
- Docker Compose for local PostgreSQL, PgBouncer, and Redis.

## Runtime Shape

Application behavior lives in `src/fastapi_template/core`. Framework and storage adapters live in `src/fastapi_template/infrastructure`. FastAPI app construction lives in `src/fastapi_template/entrypoints`, and dependency registration lives in `src/fastapi_template/ioc`.

Controllers parse HTTP requests and call use cases. Use cases expose `execute(...)`, open unit-of-work scopes for persistence, and may pass the active `uow` to focused services. SQLAlchemy repositories handle data access inside those scopes.
