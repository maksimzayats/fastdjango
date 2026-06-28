# Project Structure

```text
src/fastapi_template/
  core/              # Entities, SQLAlchemy models, DTOs, use cases, services, repositories
  foundation/        # Small base classes and shared primitives
  infrastructure/    # SQLAlchemy engine/session setup, logging, telemetry, throttling
  entrypoints/       # FastAPI application construction
  ioc/               # Dependency injection container and registrations
migrations/          # Alembic migration environment and versions
management/          # Setup and maintenance scripts
tests/               # Unit, integration, architecture, and style tests
```

## Core

Core owns application behavior plus the SQLAlchemy domain models and repositories. Delivery schemas stay in `core/<domain>/delivery/fastapi`, but use cases and services do not import FastAPI, SQLAlchemy, or the container. Use cases expose `execute(...)` and open persistence scopes through the injected `UnitOfWork`.

## Infrastructure

Core domain modules own SQLAlchemy models and repositories. `infrastructure/database` only builds the SQLAlchemy engine/session factory and opens unit-of-work transactions; application decisions stay in core use cases and services.

## Entrypoints

`entrypoints/fastapi` builds the FastAPI application, adds middleware, instruments telemetry, and registers domain controllers.
