# Architecture

Controllers are thin delivery adapters. They validate request data, call use cases, and translate application exceptions to HTTP responses.

Use cases coordinate externally meaningful application actions and expose a single public `async execute(...)` method. Services own focused reusable behavior. Persistence is accessed through a core-owned unit-of-work contract, and repositories implement data access behind core-owned contracts.

When one application action needs repository work, the use case opens the UoW inside `execute(...)`. If the action needs multiple repository operations, open one UoW and pass the active `uow` to focused collaborators. Do not nest separate UoWs for one workflow. Services may use the active `uow`, but they do not open transactions.

SQLAlchemy models live with their core domain modules, but they do not leak into controllers or use cases. Core entities and DTOs remain the application-facing data shapes, and repositories receive the active transaction session from the unit of work.

`infrastructure/database` is engine/session and unit-of-work transaction wiring only. SQLAlchemy query execution stays inside core repositories; normalization, duplicate handling, token rotation decisions, and other application rules stay in core use cases and services.

Public HTTP routes are registered as full paths such as `/api/v1/users/me`; route prefixes are not split across routers and handlers.
