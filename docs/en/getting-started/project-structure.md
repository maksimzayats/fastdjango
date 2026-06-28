# Project Structure

```text
src/fastapi_template/
  core/
    unit_of_work.py
    user/
      constants.py
      dtos.py
      entities.py
      exceptions.py
      repositories.py
      services.py
      use_cases.py
      infrastructure/persistence/sqlalchemy/
        models.py
        mappers.py
        repositories.py
      delivery/fastapi/
        schemas.py
        controllers.py
    authentication/
      dtos.py
      entities.py
      exceptions.py
      repositories.py
      services/
      use_cases.py
      infrastructure/persistence/sqlalchemy/
        models.py
        mappers.py
        repositories.py
      delivery/fastapi/
        schemas.py
        controllers.py
    health/
      exceptions.py
      repositories.py
      use_cases.py
      infrastructure/persistence/sqlalchemy/
        repositories.py
      delivery/fastapi/
        schemas.py
        controllers.py
  foundation/        # Small base classes and shared primitives
  infrastructure/    # Shared SQLAlchemy wiring, logging, telemetry, throttling
    database/
      base.py
      metadata.py
      session.py
      unit_of_work.py
  entrypoints/       # FastAPI application construction
  ioc/               # Dependency injection container and registrations
migrations/          # Alembic migration environment and versions
management/          # Setup and maintenance scripts
tests/               # Unit, integration, architecture, and style tests
```

## Core

Core is organized as vertical business modules. Inner application code lives
directly under each business package: entities, DTOs, repository interfaces,
services, use cases, and exceptions. Those inner modules do not import FastAPI,
SQLAlchemy, local infrastructure, delivery modules, or the container.

## Local Adapters

Delivery schemas and controllers live under each business package's
`delivery/fastapi` directory. Concrete SQLAlchemy models, mappers, and
repository implementations live under each business package's
`infrastructure/persistence/sqlalchemy` directory.

## Shared Infrastructure

`infrastructure/database` builds the SQLAlchemy base, metadata, engine/session
factory, and unit-of-work transaction wiring. Application decisions stay in
core use cases and services; SQLAlchemy query work stays in local repository
adapter implementations.

## Entrypoints

`entrypoints/fastapi` builds the FastAPI application, adds middleware,
instruments telemetry, and registers domain controllers.
