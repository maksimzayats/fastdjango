.PHONY: dev makemigrations migrate collectstatic update-dependencies format lint test celery-dev celery-beat-dev docs docs-build

dev:
	uv run uvicorn modern_python_template.entrypoints.fastapi.app:app --reload --host 0.0.0.0 --port 8000

makemigrations:
	uv run python management/manage.py makemigrations

migrate:
	uv run python management/manage.py migrate

collectstatic:
	uv run python management/manage.py collectstatic --no-input

update-dependencies:
	uv run python -m management.dependency_updater $(ARGS)

format:
	uv run prek run trailing-whitespace end-of-file-fixer ruff-check-fix ruff-format-fix --all-files --hook-stage manual

lint:
	uv run prek run --all-files

test:
	uv run --all-groups pytest tests/

celery-dev:
	OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run watchmedo auto-restart \
		--directory=src \
		--pattern='*.py' \
		--recursive \
		-- celery -A modern_python_template.entrypoints.celery.app worker --loglevel=DEBUG

celery-beat-dev:
	uv run watchmedo auto-restart \
		--directory=src \
		--pattern='*.py' \
		--recursive \
		-- celery -A modern_python_template.entrypoints.celery.app beat --loglevel=DEBUG

docs:
	uv run mkdocs serve --livereload -f docs/mkdocs.yml

docs-build:
	uv run mkdocs build -f docs/mkdocs.yml
