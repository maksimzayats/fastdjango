from __future__ import annotations

from datetime import UTC, datetime

from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers

TEMPLATE_URL = "https://github.com/maksimzayats/fastapi-template"


def build_project_readme(*, answers: SetupAnswers) -> str:
    sections = [
        f"# {answers.project_name}",
        "",
        f"Generated from [fastapi-template]({TEMPLATE_URL}) on {_generated_date()}.",
        "",
    ]
    sections.extend(_repository_section(answers=answers))
    sections.extend(_quick_start_section(answers=answers))
    sections.extend(_configuration_section(answers=answers))
    sections.extend(_commands_section(answers=answers))
    sections.extend(_documentation_section(answers=answers))
    sections.extend(["## License", "", "[MIT](LICENSE.md)", ""])
    return "\n".join(sections)


def _repository_section(*, answers: SetupAnswers) -> list[str]:
    if answers.repo_url is not None:
        repo_url = answers.repo_url.removesuffix(".git").rstrip("/")
        return [f"Project repository: [{repo_url}]({repo_url})", ""]

    return []


def _quick_start_section(*, answers: SetupAnswers) -> list[str]:
    sections = [
        "## Quick Start",
        "",
        "```bash",
        "uv sync --locked --all-groups",
        "```",
        "",
    ]

    docker_services = _docker_services(answers=answers)
    if docker_services:
        sections.extend(
            [
                "```bash",
                f"docker compose up -d {' '.join(docker_services)}",
                "```",
                "",
            ],
        )
    else:
        sections.extend(["No local Docker services are required for the selected defaults.", ""])

    sections.extend(
        [
            "```bash",
            "make migrate",
            "make dev",
            "```",
            "",
            (
                "The API runs at `http://localhost:8000`; health checks are available at "
                "`/api/v1/health`."
            ),
            "",
        ],
    )
    return sections


def _configuration_section(*, answers: SetupAnswers) -> list[str]:
    sections = [
        "## Configuration",
        "",
        f"- Database: {_database_label(answers=answers)}",
        f"- Redis: {_redis_label(answers=answers)}",
        f"- Logfire: {'enabled' if answers.enable_logfire else 'disabled'}",
    ]
    if answers.production_api_origin is not None:
        sections.append(f"- Production API origin: `{answers.production_api_origin}`")

    if answers.frontend_origin is not None:
        sections.append(f"- Frontend origin: `{answers.frontend_origin}`")

    sections.append("")
    return sections


def _commands_section(*, answers: SetupAnswers) -> list[str]:
    sections = [
        "Generated secrets and local connection values live in `.env`. Commit `.env.example` "
        "and keep `.env` private.",
        "",
        "## Commands",
        "",
        "| Command | Purpose |",
        "| --- | --- |",
        "| `make dev` | Run the FastAPI development server |",
        "| `make migrate` | Apply Alembic migrations |",
        "| `make test` | Run the test suite |",
        "| `make lint` | Run formatting, lint, and type checks |",
    ]
    if answers.keep_docs:
        sections.append("| `make docs` | Serve project documentation |")

    return sections


def _documentation_section(*, answers: SetupAnswers) -> list[str]:
    if not answers.keep_docs:
        return []

    sections = ["", "## Documentation", ""]
    if answers.docs_site_url is None:
        sections.extend(["Open [local docs](docs/en) or run `make docs`.", ""])
        return sections

    sections.extend(
        [
            f"Documentation is available at [{answers.docs_site_url}]({answers.docs_site_url}).",
            "",
        ],
    )
    return sections


def _docker_services(*, answers: SetupAnswers) -> list[str]:
    services: list[str] = []

    if answers.database_mode == DatabaseMode.DOCKER_POSTGRES:
        services.append("postgres")

    if answers.redis_mode == RedisMode.DOCKER_REDIS:
        services.append("redis")

    return services


def _generated_date() -> str:
    return datetime.now(tz=UTC).date().isoformat()


def _database_label(*, answers: SetupAnswers) -> str:
    if answers.database_mode == DatabaseMode.SQLITE:
        return "local SQLite"

    if answers.database_mode == DatabaseMode.REMOTE_POSTGRES:
        return "remote PostgreSQL"

    return f"local Docker PostgreSQL on port {answers.postgres_port}"


def _redis_label(*, answers: SetupAnswers) -> str:
    if answers.redis_mode == RedisMode.REMOTE_REDIS:
        return "remote Redis"

    return f"local Docker Redis on port {answers.redis_port}"
