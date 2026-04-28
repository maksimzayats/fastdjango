# fastdjango

[![CI](https://github.com/maksimzayats/fastdjango/actions/workflows/lint_test.yaml/badge.svg?branch=main)](https://github.com/maksimzayats/fastdjango/actions/workflows/lint_test.yaml)
[![Docs](https://img.shields.io/badge/docs-fastdjango.zayats.dev-blue)](https://fastdjango.zayats.dev)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)

A FastAPI + Django + Celery project template for teams that want Django's ORM
and admin, FastAPI's async delivery, and a clean application structure from the
first commit.

## Start

Recommended: create your own repository from this template on GitHub, clone it,
then run the wizard inside that checkout:

```bash
make setup
```

In this flow, the wizard detects your repository from `origin`, preserves Git
history, and only asks whether to commit the generated setup changes.

If you clone the original template directly instead, use:

```bash
git clone https://github.com/maksimzayats/fastdjango.git && cd fastdjango && make setup
```

For direct clones, let the wizard reinitialize Git so the generated project does
not keep the template history or `origin`.

The wizard renames the checkout folder to the project slug, renames the project
and Python package, writes env files, configures database, Redis, storage, docs,
public origins, observability, and Git setup for the flow you chose.

## Run Locally

For the default local PostgreSQL, Redis, and filesystem storage setup:

```bash
uv sync --locked --all-groups
docker compose up -d postgres redis
make migrate
make collectstatic
make dev
```

The API runs at `http://localhost:8000`, interactive API docs are at `/docs`,
and Django admin is mounted at `/django/admin/`.

If you choose SQLite, remote PostgreSQL, remote Redis, local MinIO, or remote
S3, follow the next-step summary printed by the wizard.

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

- `src/fastdjango/core/` - domains, models, DTOs, use cases, services, and delivery.
- `src/fastdjango/foundation/` - shared base contracts.
- `src/fastdjango/entrypoints/` - FastAPI, Django, and Celery composition roots.
- `src/fastdjango/infrastructure/` - framework and external-system integration.
- `src/fastdjango/ioc/` - dependency injection container setup.
- `management/` - repository management commands and the setup wizard.

## Documentation

Read the full documentation at [fastdjango.zayats.dev](https://fastdjango.zayats.dev),
or browse it locally in [docs/en](docs/en).

## Common Commands

| Command | Purpose |
| --- | --- |
| `make setup` | Run the one-time template setup wizard |
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
