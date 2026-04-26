dev:
	uv run uvicorn fastdjango.entrypoints.fastapi.app:app --reload --host 0.0.0.0 --port 8000

makemigrations:
	uv run src/fastdjango/manage.py makemigrations

migrate:
	uv run src/fastdjango/manage.py migrate

collectstatic:
	uv run src/fastdjango/manage.py collectstatic --no-input

format:
	uv run prek run trailing-whitespace end-of-file-fixer ruff-check-fix ruff-format-fix --all-files --hook-stage manual

lint:
	uv run prek run --all-files

test:
	uv run pytest tests/

celery-dev:
	OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run watchmedo auto-restart \
		--directory=src \
		--pattern='*.py' \
		--recursive \
		-- celery -A fastdjango.entrypoints.celery.app worker --loglevel=DEBUG

celery-beat-dev:
	uv run watchmedo auto-restart \
		--directory=src \
		--pattern='*.py' \
		--recursive \
		-- celery -A fastdjango.entrypoints.celery.app beat --loglevel=DEBUG

.PHONY: docs docs-build
docs:
	uv run mkdocs serve --livereload -f docs/mkdocs.yml

docs-build:
	uv run mkdocs build -f docs/mkdocs.yml
