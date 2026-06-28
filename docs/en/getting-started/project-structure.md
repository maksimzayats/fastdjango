# Project Structure

```text
src/fastapi_template/
  core/
    unit_of_work.py
    user/
      constants.py
      dtos/
        create_user.py
      entities/
        user.py
      exceptions/
        user_already_exists.py
        weak_password.py
      repositories/
        user.py
      services/
        password.py
        user_credential.py
        user_identity.py
      use_cases/
        create_user.py
        get_active_user_by_id.py
        get_user_by_id.py
      infrastructure/sqlalchemy/
        models/user.py
        mappers/user.py
        repositories/user.py
      delivery/fastapi/
        schemas/user.py
        controllers/create_user.py
        controllers/current_user.py
        controllers/staff_user_lookup.py
    authentication/
      dtos/
      entities/
      exceptions/
      repositories/
      services/
      use_cases/
      infrastructure/sqlalchemy/
        models/refresh_session.py
        mappers/refresh_session.py
        repositories/refresh_session.py
      delivery/fastapi/
        auth/
        schemas/
        controllers/
    health/
      exceptions/
      repositories/
      use_cases/
      infrastructure/sqlalchemy/
        repositories/health.py
      delivery/fastapi/
        schemas/health.py
        controllers/health.py
  foundation/        # Small base classes and shared primitives
  infrastructure/    # Shared SQLAlchemy wiring, logging, telemetry, throttling
    sqlalchemy/
      base.py
      metadata.py
      session.py
      unit_of_work.py
  entrypoints/       # FastAPI application construction
  ioc/               # Dependency injection container and registrations
migrations/          # Alembic migration environment and versions
management/          # Maintenance scripts
tests/               # Unit, integration, architecture, and style tests
```

## Core

Core is organized as vertical business modules. Inner application code lives
in scoped packages under each business package: entities, DTOs, repository
interfaces, services, use cases, and exceptions. A scoped file contains one
primary public class or function, such as one use case, one repository, one
DTO shape, or one entity. Those inner modules do not import FastAPI,
SQLAlchemy, local infrastructure, delivery modules, or the container.

## Local Adapters

Delivery schemas and controllers live under each business package's
`delivery/fastapi` directory. Controllers are endpoint/action scoped. Concrete SQLAlchemy models, mappers, and
repository implementations live under each business package's
`infrastructure/sqlalchemy` directory, with one model or repository per file.

## Shared Infrastructure

`infrastructure/sqlalchemy` builds the SQLAlchemy base, metadata, engine/session
factory, and unit-of-work transaction wiring. Application decisions stay in
core use cases and services; SQLAlchemy query work stays in local repository
adapter implementations.

## Entrypoints

`entrypoints/fastapi` builds the FastAPI application, adds middleware,
instruments telemetry, and registers domain controllers.
