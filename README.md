# Modern Python Template

**A FastAPI service template with clean boundaries, async persistence, and strict guardrails.**

Modern Python Template gives you a production-shaped starting point for API
services without carrying old-framework baggage. It combines FastAPI, async
SQLAlchemy, Alembic, dependency injection, authentication flows, Redis-backed
rate limiting, and strict checks in a layout that keeps application decisions
separate from adapters.

[Documentation](https://template.zayats.dev) ·
[Contribute](CONTRIBUTING.md)

## Key Benefits

- **Clean boundaries from the first commit.** Use cases, services, DTOs,
  repository contracts, delivery adapters, and SQLAlchemy adapters live in
  focused modules with architecture tests that keep those lines visible.
- **Real API behavior included.** The template ships with user registration,
  JWT issue/refresh/revoke flows, current-user and staff lookup endpoints,
  health checks, and rate limiting as working examples.
- **Async persistence without hidden transactions.** Database work goes through
  repositories inside unit-of-work scopes, with Alembic migrations and
  PostgreSQL-ready local infrastructure.
- **Strict quality checks as guardrails.** Ruff, WPS/flake8, mypy, strict
  pytest, architecture tests, meaningful docstring checks, and 100% coverage
  keep the template clear for people and future agents.

## What You Get

- A FastAPI-only service foundation with full `/api/v1/...` routes.
- SQLAlchemy async repositories and explicit unit-of-work transactions.
- Dependency injection through `diwire` without framework leakage into core
  code.
- Docker Compose services for PostgreSQL, PgBouncer, and Redis.
- Documentation that explains the boundaries, workflows, and operating model.
- Agent rules that preserve scoped files, repository usage, and test DI
  discipline.

## Why Modern Python Template

Modern Python services are easiest to evolve when the default path is already
boring in the right places: clear modules, explicit transactions, small
controllers, tested adapters, and checks that catch drift before it spreads.
This template keeps those decisions ready to copy so a new service can start
with useful structure instead of cleanup work.

## Contributing

Developer setup, commands, project layout, architecture rules, and validation
workflow live in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Modern Python Template is released under the [MIT License](LICENSE.md).
