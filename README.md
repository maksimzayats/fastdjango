# modern-python-template

[![CI](https://github.com/maksimzayats/modern-python-template/actions/workflows/lint_test.yaml/badge.svg?branch=main)](https://github.com/maksimzayats/modern-python-template/actions/workflows/lint_test.yaml)
[![Docs](https://img.shields.io/badge/docs-modern-python-template.zayats.dev-blue)](https://modern-python-template.zayats.dev)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)

A FastAPI + Django + Celery project template for teams that want Django's ORM
and admin, FastAPI's async delivery, and a clean application structure from the
first commit.

## Start

Recommended: create an empty repository for your project on GitHub, clone it,
then use the top-level [PROMPT_TEMPLATE.md](PROMPT_TEMPLATE.md) from this
repository as the setup interface. The prompt points your agent at the template
source: <https://github.com/maksimzayats/modern-python-template>.

1. Create and clone your empty project repository.
2. Set the project name and update any optional bracketed values.
3. Remove any removable capability bullets you do not want.
4. Open your empty project repository in an LLM coding agent and paste the
   edited prompt.

The agent should bring in the template source, preserve your project repo's Git
history and `origin`, rename the project and Python package, write environment
files, update docs and examples, remove omitted capabilities, refresh the
lockfile, and run validation checks. Keep the modern-python-template Base in the
prompt: FastAPI, Django ORM/admin, dependency injection, architecture guardrails,
tests, linting, and typing are the template's mandatory foundation.

## Run Locally

For a generated project that keeps local PostgreSQL, Redis, and filesystem
storage:

```bash
uv sync --locked --all-groups
docker compose up -d postgres redis
make migrate
make collectstatic
make dev
```

The API runs at `http://localhost:8000`, interactive API docs are at `/docs`,
and Django admin is mounted at `/django/admin/`.

If your edited prompt removes Redis, Celery, MinIO, S3, or other infrastructure,
use the generated README and `.env` values from the agent-led setup as the source
of truth for which services to start.

## What You Get

- FastAPI delivery with Django mounted for admin and Django URLs.
- Django ORM, migrations, authentication, admin, and typed settings.
- Celery worker and beat entrypoints backed by Redis.
- Dependency injection with `diwire` and explicit application boundaries.
- Local Docker Compose for PostgreSQL, PgBouncer, Redis, and optional MinIO.
- Storage choices for local files, local MinIO, or remote S3-compatible services.
- Strict linting, typing, architecture guardrails, and pytest coverage.

## Architecture

The main rule is deliberately simple:

```text
Controller -> Use Case / Service -> Model
```

Controllers handle FastAPI, Django, or Celery delivery concerns. Use cases and
services own application behavior, ORM access, and transaction boundaries.
Transactions use the injected `TransactionFactory`; delivery code does not call
Django models directly.

The source layout follows that rule:

- `src/modern_python_template/core/` - domains, models, DTOs, use cases, services, and delivery.
- `src/modern_python_template/foundation/` - shared base contracts.
- `src/modern_python_template/entrypoints/` - FastAPI, Django, and Celery composition roots.
- `src/modern_python_template/infrastructure/` - framework and external-system integration.
- `src/modern_python_template/ioc/` - dependency injection container setup.
- `management/` - repository management commands.

## Documentation

Read the full documentation at [modern-python-template.zayats.dev](https://modern-python-template.zayats.dev),
or browse it locally in [docs/en](docs/en).

## Common Commands

| Command | Purpose |
| --- | --- |
| `make dev` | Run the FastAPI development server |
| `make celery-dev` | Run a Celery worker |
| `make format` | Format through `prek` hooks |
| `make lint` | Run lint and type checks |
| `make test` | Run the test suite |
| `make docs` | Serve the MkDocs documentation |

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker and Docker Compose for local infrastructure choices

## License

[MIT](LICENSE.md)
