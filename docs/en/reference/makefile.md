# Makefile Commands

| Command | Purpose |
| --- | --- |
| `make dev` | Run the FastAPI development server |
| `make makemigrations` | Create an Alembic migration from model changes |
| `make migrate` | Apply Alembic migrations |
| `make check-migrations` | Fail when Alembic detects model changes without a migration |
| `make update-dependencies` | Sync dependency bounds and container image references |
| `make format` | Run formatting hooks |
| `make lint` | Run Ruff, WPS/flake8, mypy, and repository checks |
| `make test` | Run the test suite with a 100% coverage threshold |
| `make test-postgres` | Run repository and SQLAlchemy integration tests against a disposable PostgreSQL test database |
| `make docs` | Serve documentation locally |
| `make docs-build` | Build static documentation |

`make test-postgres` resets the target schema before running tests. Set
`INTEGRATION_DATABASE_URL` to a PostgreSQL database whose name starts with
`test_` or ends with `_test`.
