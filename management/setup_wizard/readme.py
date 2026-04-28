from __future__ import annotations

from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers, StorageMode


def build_project_readme(*, answers: SetupAnswers) -> str:  # noqa: PLR0912
    sections = [
        f"# {answers.project_name}",
        "",
        "Application generated from the FastDjango template.",
        "",
    ]

    if answers.repo_url is not None:
        sections.extend([f"Repository: [{answers.repo_url}]({answers.repo_url})", ""])

    sections.extend(
        [
            "## Quick Start",
            "",
            "```bash",
            "uv sync --locked --all-groups",
            "```",
            "",
        ],
    )

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
        sections.extend(
            [
                "The selected database, Redis, and storage defaults do not require local Docker services.",
                "",
            ],
        )

    if answers.storage_mode == StorageMode.MINIO:
        sections.extend(
            [
                "```bash",
                "docker compose up minio-create-buckets",
                "```",
                "",
            ],
        )

    sections.extend(
        [
            "```bash",
            "make migrate",
            "make collectstatic",
            "make dev",
            "```",
            "",
            "The API runs at `http://localhost:8000`; health checks are available at `/v1/health`.",
            "",
            "## Configuration",
            "",
            f"- Database: {_database_label(answers=answers)}",
            f"- Redis: {_redis_label(answers=answers)}",
            f"- Storage: {_storage_label(answers=answers)}",
            f"- Logfire: {'enabled' if answers.enable_logfire else 'disabled'}",
            "",
        ],
    )

    if answers.production_api_origin is not None:
        sections.insert(-1, f"- Production API origin: `{answers.production_api_origin}`")

    if answers.frontend_origin is not None:
        sections.insert(-1, f"- Frontend origin: `{answers.frontend_origin}`")

    sections.extend(
        [
            "Generated secrets and local connection values live in `.env`. Commit `.env.example` and keep `.env` private.",
            "",
            "## Commands",
            "",
            "| Command | Purpose |",
            "| --- | --- |",
            "| `make dev` | Run the FastAPI development server |",
            "| `make migrate` | Apply Django migrations |",
            "| `make collectstatic` | Collect Django static files |",
            "| `make test` | Run the test suite |",
            "| `make lint` | Run formatting, lint, and type checks |",
        ],
    )

    if answers.keep_docs:
        sections.append("| `make docs` | Serve project documentation |")

    if answers.keep_docs:
        sections.extend(["", "## Documentation", ""])
        if answers.docs_site_url is None:
            sections.extend(["Open [local docs](docs/en) or run `make docs`.", ""])
        else:
            sections.extend(
                [
                    f"Documentation is available at [{answers.docs_site_url}]({answers.docs_site_url}).",
                    "",
                ],
            )

    sections.extend(["## License", "", "[MIT](LICENSE.md)", ""])
    return "\n".join(sections)


def _docker_services(*, answers: SetupAnswers) -> list[str]:
    services: list[str] = []

    if answers.database_mode == DatabaseMode.DOCKER_POSTGRES:
        services.append("postgres")

    if answers.redis_mode == RedisMode.DOCKER_REDIS:
        services.append("redis")

    if answers.storage_mode == StorageMode.MINIO:
        services.append("minio")

    return services


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


def _storage_label(*, answers: SetupAnswers) -> str:
    if answers.storage_mode == StorageMode.LOCAL:
        return "local filesystem"

    if answers.storage_mode == StorageMode.MINIO:
        return f"local MinIO on ports {answers.minio_api_port} and {answers.minio_console_port}"

    return "remote S3-compatible storage"
