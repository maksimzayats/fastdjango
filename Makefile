dev:
	uv run uvicorn delivery.http.app:app --reload --host 0.0.0.0 --port 8000

makemigrations:
	uv run src/manage.py makemigrations

migrate:
	uv run src/manage.py migrate

collectstatic:
	uv run src/manage.py collectstatic --no-input

format:
	uv run ruff format .
	uv run ruff check --fix-only .

lint:
	uv run ruff check .
	uv run ty check .
	uv run pyrefly check src/
	uv run --env-file .env.test.example mypy src/ tests/

test:
	uv run pytest tests/

celery-dev:
	OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run watchmedo auto-restart \
		--directory=src \
		--pattern='*.py' \
		--recursive \
		-- celery -A delivery.tasks.app worker --loglevel=DEBUG

celery-beat-dev:
	uv run watchmedo auto-restart \
		--directory=src \
		--pattern='*.py' \
		--recursive \
		-- celery -A delivery.tasks.app beat --loglevel=DEBUG

.PHONY: docs docs-build
docs:
	uv run mkdocs serve --livereload -f docs/mkdocs.yml

docs-build:
	uv run mkdocs build -f docs/mkdocs.yml
