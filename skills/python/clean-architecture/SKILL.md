---
name: clean-architecture
description: "Use when creating or refactoring Python applications toward clean src package architecture with class-based use cases/services, focused boundaries, pydantic-settings configuration, API route guidance, testing/tooling guardrails for this architecture, AGENTS.md/CLAUDE.md repo instructions, and diwire Injected[...] dependency injection. Useful for Python clean architecture, DI, settings, configuration, ENV vars, API routes, service boundaries, framework adapters, architecture tests, or moving logic out of delivery code. Do not use for non-Python repos or generic formatting-only cleanup."
---

# Clean Architecture Skill

Use this skill to create or reshape Python repos toward pragmatic clean
architecture:

- `src/<package_name>` import-package layout;
- Python 3.14 by default for new repos unless the user asks for another
  version;
- class-based use cases and focused services;
- clean delivery, core, infrastructure, entrypoint, and composition boundaries;
- dependency injection through `diwire` and `Injected[...]`;
- configuration through `pydantic-settings` classes backed by environment
  variables;
- API route delivery guidance with full `/api/v1/...` paths;
- tests, tooling, style, and agent instructions that enforce the boundaries.

Keep the main file lean. Load the reference files below only when the task
touches that area.

## First Steps

Before editing an existing repo:

1. Read `pyproject.toml`, package layout, tests, framework entrypoints, existing
   dependency-injection/container code, and existing `AGENTS.md` or `CLAUDE.md`
   files.
2. Find the import package name. Prefer the existing package under `src/`. If
   creating a new repo, derive it from the project name by normalizing to a valid
   Python identifier, for example `order-service` -> `order_service`.
3. For new repos, default to Python 3.14 unless the user asks for a different
   version. For existing repos, preserve the repo's configured Python version
   unless the user asks to change it.
4. Preserve behavior. Move code behind cleaner boundaries in small vertical
   slices instead of doing a broad rewrite.
5. Adapt delivery details to the framework the user names or the repo already
   uses. This skill is framework-agnostic.
6. Load only the references needed for the task.

## Reference Router

Read these files as needed:

| Task need | Reference |
| --- | --- |
| Package layout, layers, use cases, services, boundaries, DTOs, schemas, and abstractions | [references/architecture.md](references/architecture.md) |
| `diwire`, `Injected[...]`, container creation, explicit registration, and test overrides | [references/diwire.md](references/diwire.md) |
| Pytest layout, unit/integration/architecture/style tests, fixtures, and boundary checks | [references/testing.md](references/testing.md) |
| `uv`, `ruff`, `mypy`, formatting, linting, type-checking, and pre-commit-style checks | [references/tooling.md](references/tooling.md) |
| Python class style, dataclass shape, naming, method signatures, imports, and small code snippets | [references/style.md](references/style.md) |
| Settings, configuration classes, environment variables, and injecting configuration into services/adapters | [references/settings.md](references/settings.md) |
| HTTP API route/controller layout, full `/api/v1/...` route paths, request/response mapping, and route boundary rules | [references/api-routes.md](references/api-routes.md) |
| Creating or updating target-repo `AGENTS.md` and `CLAUDE.md` files | [references/agent-instructions.md](references/agent-instructions.md) |
| Incremental migration workflow for existing repos | [references/migration.md](references/migration.md) |

If a task crosses multiple areas, start with the narrowest reference that covers
the main change, then add another only when the work touches that area. For
example, start a new use case with `architecture.md`; add `diwire.md` only when
wiring changes, `style.md` when writing class/typing examples, and `testing.md`
when adding or changing tests.

## Hard Rules

Use these rules unless the existing repo has a stronger local convention:

- Application classes receive dependencies; they do not import a container or
  call `container.resolve()`.
- New repos use Python 3.14 by default unless the user asks for another version.
- Only `ioc/`, outermost entrypoints, and tests may create or use
  `diwire.Container`.
- Use cases and services do not import delivery concerns such as routers,
  request/response schemas, CLI parsers, task decorators, or framework objects.
- All business/application logic belongs in `core/`.
- `infrastructure/` must not contain business/application logic. Use it only for
  technical building blocks such as external clients, persistence adapters,
  framework adapters, and IO implementations.
- External IO and framework-bound dependencies live at the edge or behind a
  justified adapter.
- Classes that need runtime configuration receive a `pydantic-settings`
  settings object backed by environment variables.
- Public HTTP API routes are defined as full paths beginning with `/api/v1`.
  Use the chosen framework's route API, but pass full public paths and do not
  split paths across router/base prefixes and route-local fragments.
- Do not add any code to `__init__.py` files, including comments, imports,
  exports, constants, or package metadata, unless the user explicitly asks for
  it.
- Prefer `@dataclass(kw_only=True, slots=True)` for application classes. Add
  `frozen=True` as well for immutable DTOs.
- Define type aliases with `: TypeAlias`.
- Do not introduce an ABC, interface, or protocol just because dependency
  injection is present.
- Use ABC classes only when a real boundary needs an abstraction. If one
  concrete implementation is enough, inject the concrete class.
- Prefer clean, focused services over generic `Manager`, `Helper`, `Utils`, or
  vague `Handler` classes.
- Do not create empty folders or tests just to satisfy an architecture diagram.

## Standard Workflow

When implementing:

1. Identify the user-facing action or behavior being added or migrated.
2. Put delivery parsing and serialization in the framework-specific adapter.
3. Put externally meaningful application flow in a use case.
4. Put reusable focused behavior in services.
5. Keep all business/application decisions in `core/`; use `infrastructure/`
   only for technical building blocks and adapters.
6. Define settings classes above the class that consumes them when a class needs
   runtime configuration.
7. Inject dependencies with `Injected[...]`; do not instantiate collaborators
   inside use cases/services unless they are simple values.
8. Register dependencies only when auto-wiring cannot express the binding.
9. Add focused tests and architecture checks only where they protect behavior or
   a boundary that matters.

For existing repos, migrate one user-facing action at a time. Move that path
behind a use case/service boundary, wire it with `diwire`, run the relevant
checks, then repeat.

## Before Finishing

Check:

- New-repo tooling defaults to Python 3.14 unless the user asked otherwise.
- Core use cases/services do not import delivery adapters, framework entrypoint
  objects, request/response schemas, or `diwire.Container`.
- Explicit container registrations are limited to abstractions, factories,
  existing instances, or external adapter bindings.
- `infrastructure/` contains only technical building blocks/adapters, not
  business/application logic.
- Tests override dependencies before resolving the object graph.
- `foundation/`, if present, contains only stable cross-layer primitives.
- `__init__.py` files are empty unless the user explicitly requested content.
- Dataclasses use `kw_only=True, slots=True` by default.
- Type aliases use `: TypeAlias`, not plain assignment.
- Repo agent instructions, if added or changed, are concise and command-focused.

Use the repo's existing commands first. Typical checks are:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

Report exactly which checks ran and any checks that could not run.
