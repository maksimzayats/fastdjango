# Architecture

Controllers are thin delivery adapters. They validate request data, call use cases, and translate application exceptions to HTTP responses.

Use cases coordinate externally meaningful application actions and expose a single public `async execute(...)` method. Services own focused reusable behavior. Database access goes through a core-owned unit-of-work contract, and repositories implement data access behind core-owned contracts.

When one application action needs repository work, the use case opens the UoW inside `execute(...)`. If the action needs multiple repository operations, open one UoW and pass the active `uow` to focused collaborators. Do not nest separate UoWs for one workflow. Services may use the active `uow`, but they do not open transactions.

`core` is a vertical business-module namespace. Inner application code lives in scoped packages under each business package: entities, DTOs, exceptions, repository interfaces, services, and use cases. Local delivery adapters live under paths such as `core/user/delivery/fastapi`; local SQLAlchemy adapters live under paths such as `core/user/infrastructure/sqlalchemy`.

Use packages with scoped files instead of bucket modules. A use-case file contains one use case, a controller file contains one endpoint/action controller, a repository file contains one domain-model repository, and a SQLAlchemy model file contains one table/domain model. Keep `__init__.py` files empty and import classes from their direct modules.

Repository interfaces are inner core contracts and do not import SQLAlchemy. Concrete SQLAlchemy models, mappers, and repositories live in local business infrastructure. Local infrastructure may import inner entities, DTOs, exceptions, and repository interfaces, but it must not import delivery. Delivery modules map request schemas to DTOs and must not import local infrastructure.

`infrastructure/sqlalchemy` is shared SQLAlchemy base, metadata, engine/session, and unit-of-work transaction wiring. SQLAlchemy query execution stays inside local SQLAlchemy adapters owned by the module that needs the query; normalization, duplicate handling, token rotation decisions, and other application rules stay in core use cases and services.

Public HTTP routes are registered as full paths such as `/api/v1/users/me`; route prefixes are not split across routers and handlers.

Public classes, functions, methods, and constructors in application code use concise Google-style docstrings that explain contracts, boundaries, domain meaning, side effects, or failure semantics. Placeholder docstrings such as `Define X.`, `Run X.`, or `Returns: The operation result.` are blocked by style tests. The template keeps Ruff, WPS/flake8, mypy, strict pytest settings, and architecture tests as guardrails for these conventions.
