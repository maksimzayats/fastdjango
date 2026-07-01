.PHONY: dev makemigrations migrate check-migrations update-dependencies format lint test test-postgres docs docs-build

dev:
	uv run uvicorn fastapi_template.entrypoints.fastapi.app:app --reload --host 0.0.0.0 --port 8000

makemigrations:
	uv run alembic revision --autogenerate

migrate:
	uv run alembic upgrade head

check-migrations:
	uv run alembic check

update-dependencies:
	uv run python -m management.dependency_updater $(ARGS)

format:
	uv run prek run trailing-whitespace end-of-file-fixer ruff-check-fix ruff-format-fix --all-files --hook-stage manual

lint:
	uv run prek run --all-files

test:
	uv run --all-groups pytest tests/

test-postgres:
	@test -n "$$INTEGRATION_DATABASE_URL" || (echo "INTEGRATION_DATABASE_URL is required for make test-postgres"; exit 1)
	@case "$$INTEGRATION_DATABASE_URL" in postgres://*|postgresql://*) ;; *) echo "INTEGRATION_DATABASE_URL must be a PostgreSQL URL"; exit 1 ;; esac
	@uv run python -c 'import os, sys; from urllib.parse import urlparse; database = urlparse(os.environ["INTEGRATION_DATABASE_URL"]).path.strip("/"); sys.exit(0 if database.startswith("test_") or database.endswith("_test") else 1)' || (echo "INTEGRATION_DATABASE_URL database name must start with test_ or end with _test because make test-postgres resets its schema"; exit 1)
	uv run --all-groups pytest tests/integration/core/user/infrastructure/sqlalchemy/repositories tests/integration/core/authentication/infrastructure/sqlalchemy/repositories tests/integration/core/health/infrastructure/sqlalchemy tests/integration/infrastructure/sqlalchemy --no-cov

docs:
	uv run mkdocs serve --livereload -f docs/mkdocs.yml

docs-build:
	uv run mkdocs build -f docs/mkdocs.yml
