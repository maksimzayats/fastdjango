# Quick Start

Install dependencies:

```bash
uv sync --locked --all-groups
```

Create a local `.env` from the example:

```bash
cp .env.example .env
```

Start local services:

```bash
docker compose up -d postgres redis
```

Apply database migrations:

```bash
make migrate
```

Run the API:

```bash
make dev
```

The API is available at `http://localhost:8000`. The health endpoint is `GET /api/v1/health`.

Run checks:

```bash
make lint
make test
```

`make lint` runs Ruff, wemake-python-styleguide, mypy, and repository checks.
`make test` enforces 100% coverage for counted source files.
