# Architecture

Controllers are thin delivery adapters. They validate request data, call use cases, and translate application exceptions to HTTP responses.

Use cases coordinate externally meaningful application actions and expose a single public `async execute(...)` method. Services own focused reusable behavior. Persistence is accessed through a core-owned unit-of-work contract, and repositories implement data access behind core-owned contracts.

When one application action needs repository work, the use case opens the UoW inside `execute(...)`. If the action needs multiple repository operations, open one UoW and pass the active `uow` to focused collaborators. Do not nest separate UoWs for one workflow. Services may use the active `uow`, but they do not open transactions.

`core` is a vertical business-module namespace. Inner application code lives directly under each business package: entities, DTOs, exceptions, repository interfaces, services, and use cases. Local delivery adapters live under paths such as `core/user/delivery/fastapi`; local SQLAlchemy adapters live under paths such as `core/user/infrastructure/persistence/sqlalchemy`.

Repository interfaces are inner core contracts and do not import SQLAlchemy. Concrete SQLAlchemy models, mappers, and repositories live in local business infrastructure. Local infrastructure may import inner entities, DTOs, exceptions, and repository interfaces, but it must not import delivery. Delivery modules map request schemas to DTOs and must not import local infrastructure.

`infrastructure/database` is shared engine/session and unit-of-work transaction wiring only. SQLAlchemy query execution stays inside local SQLAlchemy repository implementations; normalization, duplicate handling, token rotation decisions, and other application rules stay in core use cases and services.

Public HTTP routes are registered as full paths such as `/api/v1/users/me`; route prefixes are not split across routers and handlers.

Public classes, functions, methods, and constructors in application code use concise Google-style docstrings. The template keeps Ruff, WPS/flake8, mypy, strict pytest settings, and architecture tests as guardrails for these conventions.
