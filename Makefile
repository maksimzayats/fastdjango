.PHONY: dev makemigrations migrate setup update-dependencies format lint test docs docs-build

dev:
	uv run uvicorn fastapi_template.entrypoints.fastapi.app:app --reload --host 0.0.0.0 --port 8000

makemigrations:
	uv run alembic revision --autogenerate

migrate:
	uv run alembic upgrade head

setup:
	uv run --group setup python -m management.setup_wizard $(ARGS)

update-dependencies:
	uv run python -m management.dependency_updater $(ARGS)

format:
	uv run prek run trailing-whitespace end-of-file-fixer ruff-check-fix ruff-format-fix --all-files --hook-stage manual

lint:
	uv run prek run --all-files

test:
	uv run --all-groups pytest tests/

docs:
	uv run mkdocs serve --livereload -f docs/mkdocs.yml

docs-build:
	uv run mkdocs build -f docs/mkdocs.yml
