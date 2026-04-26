# FastDjango Agent Rules

## Work Rules

- Understand the exact request; do not solve a different nearby problem.
- Run `git status --short` before editing and preserve user changes.
- Read existing code before changing structure, imports, names, or layers.
- Search with `rg` / `rg --files`.
- Prefer the smallest readable fix that matches the current codebase.
- Do not hide simple runtime code behind helper/cast/abstraction workarounds.
- For checker false positives, use the narrowest local ignore on the exact line.
- Keep ignores clear and non-repetitive.
- Do not commit, push, reset, or revert unless explicitly asked.
- Use `prek` for format, lint, and type-check hooks; avoid direct tool commands unless isolating a failure.
- Validate changes before the final response; report exact checks that ran.
- Report checks that ran; say when important checks were skipped or failed.

## Project Shape

- Python 3.14+ FastAPI + Django + Celery template.
- Dependency injection uses `diwire`.
- Prefer practical clean architecture: clear boundaries, minimal ceremony.
- `foundation/`: neutral base classes and contracts.
- `core/`: domain modules, models, DTOs, use cases, services, and owned delivery.
- `entrypoints/`: FastAPI, Django, and Celery composition roots.
- `infrastructure/`: framework and external-system integration.
- `ioc/`: dependency injection container setup.

## Layering

- Controllers call use cases or services; use cases and services own ORM access.
- Controllers must not query Django models directly.
- Admin, migrations, and tests may touch models directly.
- Delivery folders are infrastructure-specific: `fastapi`, `django`, `celery`.
- Delivery schemas stay in delivery layers; DTOs stay near use cases.
- Infrastructure must not depend on core delivery details.
- Shared code must be genuinely shared, not a dumping ground.

## Class Markers

- Use `BaseService`, `BaseUseCase`, `BaseFactory`, and `BaseConfigurator`.
- Use `BaseController`, `BaseAsyncController`, and `BaseTransactionController`.
- Use `BaseDTO`, `BaseFastAPISchema`, and `BaseCelerySchema`.
- Use `BaseTasksRegistry` for task registries.
- Use `BaseThrottler` for FastAPI throttlers.
- Use `ApplicationSettings` only for app-wide environment/version/time-zone settings.
- Annotate injected constructor dependencies with `diwire.Injected[...]` so DI-provided fields are explicit to readers.
- Separate injected dependency fields from other dataclass fields with an empty line.

## Exception Contracts

- Services and use cases must expose every raised or caught exception that may be handled by callers as a class-level contract.
- Annotate exception contracts with bare `ClassVar`, not generic `ClassVar[type[...]]`.
- Raise and catch service/use-case exceptions through those contracts, for example `raise self.WEAK_PASSWORD_ERROR` or `except self.USER_NOT_FOUND_ERROR`.
- Delivery code must handle domain exceptions through the responsible service or use-case contract, not by importing domain exception modules directly.

## Coding

- Follow existing file names, imports, and local patterns.
- Keep edits scoped to the request.
- Do not add backward-compatibility layers unless explicitly requested.
- Use `apply_patch` for manual edits.
- Prefer explicit readable code over clever typing workarounds.
- Use casts only at real third-party or protocol typing boundaries.
- In `infrastructure/django/settings.py`, keep direct settings construction with line-local ignores.
- Do not replace direct settings construction with helper functions or casts.
- Add comments only for non-obvious behavior.
- Tests should cover template behavior, not framework internals.
- Keep docs short, current, and user-friendly.

## Commands

- Install: `uv sync --locked --all-groups`
- Start services: `docker compose up -d postgres redis minio`
- Prepare app: `docker compose up minio-create-buckets migrations collectstatic`
- Run app: `make dev`
- Run Celery worker: `make celery-dev`
- Run Celery beat: `make celery-beat-dev`
- Format via `prek`: `make format`
- Lint/type check via `prek`: `make lint`
- Test with coverage: `make test`
- Test without coverage: `uv run pytest tests/ --no-cov`
- Docs: `make docs` / `make docs-build`
