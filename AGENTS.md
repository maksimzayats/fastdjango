# FastAPI Template Agent Rules

## Work Rules

- Understand the exact request; do not solve a nearby problem.
- Run `git status --short` before editing and preserve user changes.
- Read existing code before changing structure, imports, names, or layers.
- Search with `rg` / `rg --files`.
- Prefer the smallest readable fix that matches the current codebase.
- Do not commit, push, reset, or revert unless explicitly asked.
- Use `prek` through `make format` and `make lint` for checks.
- Validate changes before the final response and report exact checks.

## Project Shape

- Python 3.14+ FastAPI template.
- Dependency injection uses `diwire`.
- Persistence uses async SQLAlchemy, Alembic, repositories, and a unit-of-work boundary.
- `foundation/`: neutral base classes and shared primitives.
- `core/`: entities, SQLAlchemy domain models, DTOs, use cases, services, repositories, and unit-of-work contracts.
- `entrypoints/`: FastAPI composition root.
- `infrastructure/`: SQLAlchemy engine/session setup, unit-of-work transaction wiring, logging, telemetry, throttling, and external adapters.
- `ioc/`: dependency injection container setup.

## Layering

- Controllers call use cases or services; controllers do not query persistence directly.
- Use cases and services do not import FastAPI, SQLAlchemy, entrypoints, or the IoC container.
- Use cases expose exactly one public method: `async def execute(...)`.
- Use cases open persistence scopes through injected `UnitOfWork` with `async with self._uow as uow`.
- Application actions that need multiple repository operations open one UoW in `execute(...)` and pass the active `uow` to focused collaborators; do not nest UoWs for one workflow.
- Services may receive an active `uow` when they need repository access, but services must not open transactions.
- SQLAlchemy domain models live with their core domain modules and use `*Model` names.
- Repositories live in core and receive the active session from the unit of work; repositories do not open sessions or transactions.
- `infrastructure/database` is only for engine/session creation and unit-of-work transaction wiring.
- Infrastructure must not define domain models, repositories, query behavior, normalization, duplicate decisions, token rotation decisions, or other application rules.
- SQLAlchemy query construction and execution must stay inside core repositories.
- Delivery schemas stay in delivery layers; DTOs stay near use cases.
- Public HTTP routes must be full `/api/v1/...` paths.
- Infrastructure must not depend on core delivery details.
- Shared code must be genuinely shared, not a dumping ground.

## Class Markers

- Use `BaseService`, `BaseUseCase`, `BaseFactory`, and `BaseConfigurator`.
- Use `BaseAsyncController` for FastAPI controllers.
- Use `BaseDTO` and `BaseFastAPISchema`.
- Use `BaseThrottler` for FastAPI throttlers.
- Annotate injected constructor dependencies with `diwire.Injected[...]`.
- Separate injected dependency fields from other dataclass fields with an empty line.

## Exception Contracts

- Services and use cases expose every raised or caught exception that callers may handle as a class-level contract.
- Annotate exception contracts with bare `ClassVar`, not generic `ClassVar[type[...]]`.
- Delivery code handles domain exceptions through the responsible service or use-case contract.

## Coding

- Follow existing file names, imports, and local patterns.
- Keep edits scoped to the request.
- Do not add backward-compatibility layers unless explicitly requested.
- Use `apply_patch` for manual edits.
- Prefer explicit readable code over clever typing workarounds.
- Service and use-case methods must make custom arguments keyword-only with `*`.
- Prefer guard clauses and early returns/raises when they make code flatter.
- Do not invent local `Protocol` types when a concrete project type or core ABC exists.
- Use casts only at real third-party or protocol typing boundaries.
- Add comments only for non-obvious behavior.
- Tests should cover behavior or architectural contracts, not framework internals.
- Keep docs short, current, and user-friendly.

## Commands

- Install: `uv sync --locked --all-groups`
- Start services: `docker compose up -d postgres redis`
- Run migrations: `make migrate`
- Run app: `make dev`
- Format: `make format`
- Lint/type check: `make lint`
- Test with coverage: `make test`
- Test without coverage: `uv run pytest tests/ --no-cov`
- Docs: `make docs` / `make docs-build`
