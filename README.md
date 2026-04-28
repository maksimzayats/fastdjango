# Fast Django

A FastAPI + Django + Celery project template for teams that want Django's ORM
and admin, FastAPI's async delivery, and a clean application structure from the
first commit.

## Start Here

Fast Django is meant to be cloned and customized through the setup wizard.

```bash
git clone https://github.com/MaksimZayats/fastdjango.git my-api
cd my-api
make setup
```

The wizard renames the project and Python package, writes a generated `.env`,
lets you choose database, Redis, storage, docs, public origins, and Logfire
defaults, then prints the exact next commands for your choices.

To preview the changes first:

```bash
make setup ARGS="--dry-run"
```

## Run Locally

Install dependencies after setup:

```bash
uv sync --locked --all-groups
```

For local Docker PostgreSQL, local Docker Redis, and local filesystem storage:

```bash
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

- FastAPI HTTP delivery with Django mounted for admin and Django URLs.
- Django ORM, migrations, admin, authentication model, and typed settings.
- Celery worker and beat entrypoints using Redis.
- Dependency injection with `diwire` and explicit base contracts.
- Local Docker Compose for PostgreSQL, PgBouncer, Redis, and optional MinIO.
- Storage modes for local filesystem, local MinIO, or remote S3-compatible services.
- Logfire/OpenTelemetry integration that is off by default until configured.
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

- `src/fastdjango/core/` - domains, models, DTOs, use cases, services, and domain delivery.
- `src/fastdjango/foundation/` - shared base contracts.
- `src/fastdjango/entrypoints/` - FastAPI, Django, and Celery composition roots.
- `src/fastdjango/infrastructure/` - framework and external-system integration.
- `src/fastdjango/ioc/` - dependency injection container setup.
- `management/` - repository management commands, including `manage.py` and the setup wizard.

## Documentation

- [Quick Start](docs/en/getting-started/quick-start.md)
- [Project Structure](docs/en/getting-started/project-structure.md)
- [Development Environment](docs/en/getting-started/development-environment.md)
- [Tutorial: Build a Todo List](docs/en/tutorial/index.md)
- [Concepts](docs/en/concepts/index.md)
- [Reference](docs/en/reference/index.md)

## Useful Commands

| Command | Purpose |
| --- | --- |
| `make setup` | Run the one-time template setup wizard |
| `make dev` | Run the FastAPI development server |
| `make migrate` | Apply Django migrations |
| `make collectstatic` | Collect Django static files |
| `make celery-dev` | Run a Celery worker |
| `make celery-beat-dev` | Run Celery beat |
| `make update-dependencies` | Update uv lock, dependency bounds, CI pins, and container image pins |
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
