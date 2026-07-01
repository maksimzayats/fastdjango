# Modern Python Template Agent Rules

## Work Rules

- Understand the exact request; do not solve a nearby problem.
- Run `git status --short` before editing and preserve user changes.
- Read existing code before changing structure, imports, names, or layers.
- Search with `rg` / `rg --files`.
- Prefer the smallest readable fix that matches the current codebase.
- Do not commit, push, reset, or revert unless explicitly asked.
- Use `prek` through `make format` and `make lint` for checks.
- Public classes, functions, methods, and constructors in `src/` and
  `management/` need concise Google-style docstrings that explain contract,
  boundary behavior, domain meaning, side effects, or failure semantics.
- Validate changes before the final response and report exact checks.

## Project Shape

- Python 3.14+ FastAPI template.
- Dependency injection uses `diwire`.
- Database access uses async SQLAlchemy, Alembic, repositories, and a unit-of-work boundary.
- `foundation/`: neutral base classes and shared primitives.
- `core/`: vertical business modules. Inner entities, DTOs, repository ports,
  services, use cases, and exceptions live in scoped packages under each business
  package. Local delivery adapters live under paths such as `core/user/delivery/fastapi`.
  Local concrete infrastructure adapters live under paths such as
  `core/user/infrastructure/sqlalchemy`.
- `entrypoints/`: FastAPI composition root.
- `infrastructure/`: SQLAlchemy engine/session setup, unit-of-work transaction wiring, logging, telemetry, throttling, and external adapters.
- `ioc/`: dependency injection container setup.

## Layering

- Controllers call use cases or services; controllers do not query the database directly.
- Use cases and services do not import FastAPI, SQLAlchemy, entrypoints, or the IoC container.
- Use cases expose exactly one public method: `async def execute(...)`.
- Use cases open unit-of-work scopes through injected `UnitOfWork` with `async with self._uow as uow`.
- Application actions that need multiple repository operations open one UoW in `execute(...)` and pass the active `uow` to focused collaborators; do not nest UoWs for one workflow.
- Services may receive an active `uow` when they need repository access, but services must not open transactions.
- Only files outside `delivery/` and `infrastructure/` are inner core.
- Repository interfaces live in inner core and must not import SQLAlchemy.
- SQLAlchemy models, mappers, and concrete repository implementations live in
  local business infrastructure, for example
  `core/authentication/infrastructure/sqlalchemy`.
- Local infrastructure may import inner entities, DTOs, repository interfaces,
  and exceptions; it must not import delivery.
- Local delivery may import schemas, DTOs, use cases, and delivery helpers; it
  must not import local infrastructure or repositories.
- `infrastructure/sqlalchemy/unit_of_work.py` may import local SQLAlchemy repository
  implementations to assemble one transaction boundary.
- `ioc/registry.py` may register concrete adapters.
- `infrastructure/sqlalchemy` is shared SQLAlchemy base, metadata,
  engine/session creation, and unit-of-work transaction wiring.
- Infrastructure adapters must not define application rules such as
  normalization, duplicate decisions, token rotation decisions, or permission
  checks.
- SQLAlchemy query construction and execution must stay inside local SQLAlchemy
  adapters owned by the business module that needs the query.
- Repositories may call `flush()`, but only the UoW may commit, roll back, close
  sessions, open transactions, create engines, or create session factories.
- Delivery schemas stay in delivery layers; DTOs stay near use cases.
- Public HTTP routes must be full `/api/v1/...` paths.
- Infrastructure must not depend on core delivery details.
- Shared code must be genuinely shared, not a dumping ground.

## Scoped Files

- These rules apply to `src/` and `management/`.
- Use packages with scoped files instead of aggregate modules. Do not add
  `use_cases.py`, `dtos.py`, `services.py`, `repositories.py`, `schemas.py`,
  `controllers.py`, `models.py`, `exceptions.py`, or similar bucket files.
- A scoped source file has one primary public class or one public function.
  Tightly owned helper classes ending in `Settings`, `Result`, or `State` may
  live beside their owner.
- One use case file contains one use case. One controller file contains one
  endpoint/action controller. One repository file contains one domain-model
  repository. One SQLAlchemy model file contains one table/domain model.
- Keep `__init__.py` files empty. Import concrete classes from their direct
  modules and do not add alias modules or package re-exports.

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
- Use `apply_patch` for manual edits.
- Prefer explicit readable code over clever typing workarounds.
- Service and use-case methods must make custom arguments keyword-only with `*`.
- Prefer guard clauses and early returns/raises when they make code flatter.
- Do not invent local `Protocol` types when a concrete project type or core ABC exists.
- Use casts only at real third-party or protocol typing boundaries.
- Add comments only for non-obvious behavior.
- Do not write placeholder docstrings such as `Define X.`, `Run X.`, or
  `Returns: The operation result.` A docstring must help a future reader or
  agent understand why the object exists or how to use it. Remove private
  helper docstrings when no meaningful contract exists.
- Keep Ruff, wemake-python-styleguide, mypy, and pytest strictness passing.
- Tests should cover behavior or architectural contracts, not framework internals.
- Coverage must remain at 100% for counted source files; omit only genuinely
  configuration-only/import-only modules.
- Keep docs short, current, and user-friendly.

## Testing DI

- Unit tests may instantiate the subject directly with deterministic fakes when
  that keeps the behavior under test explicit.
- Infrastructure adapter tests may instantiate concrete adapters directly when
  the adapter lifecycle or failure mode is the behavior under test.
- Integration tests use fixtures from the nearest `conftest.py`; do not rebuild
  available factory fixtures such as `TestClientFactory`, `TestUserFactory`, or
  `TestRefreshSessionFactory` inside a test.
- Override container dependencies before creating the test client. The shared
  test client factory resolves `FastAPIFactory` only after overrides are in
  place.
- Delivery integration tests must not import SQLAlchemy, SQLAlchemy models,
  shared SQLAlchemy session factories, or local SQLAlchemy adapters. Prepare
  database state through test factories that use `UnitOfWork` and repositories.
- Tests that need unreachable domain states, such as inactive users with refresh
  sessions, should add focused test-factory helpers instead of opening raw
  sessions or issuing SQL in delivery tests.

## Commands

- Install: `uv sync --locked --all-groups`
- Start services: `docker compose up -d postgres redis`
- Run migrations: `make migrate`
- Check migration drift: `make check-migrations`
- Run app: `make dev`
- Format: `make format`
- Lint/type check: `make lint` (Ruff, WPS/flake8, mypy, and repository checks)
- Test with coverage: `make test` (100% coverage threshold)
- Test PostgreSQL repository behavior: `INTEGRATION_DATABASE_URL=... make test-postgres`
- Test without coverage: `uv run pytest tests/ --no-cov`
- Docs: `make docs` / `make docs-build`
