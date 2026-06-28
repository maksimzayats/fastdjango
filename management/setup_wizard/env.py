from __future__ import annotations

import secrets
from dataclasses import dataclass
from json import dumps
from urllib.parse import urlsplit

from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers


@dataclass(frozen=True, kw_only=True)
class EnvCredentials:
    jwt_key: str
    postgres_key: str
    redis_key: str


def build_env_content(*, answers: SetupAnswers) -> str:
    return _join_env_lines(
        lines=_build_base_env_lines(
            answers=answers,
            credentials=EnvCredentials(
                jwt_key=secrets.token_urlsafe(48),
                postgres_key=secrets.token_urlsafe(32),
                redis_key=secrets.token_urlsafe(32),
            ),
            real_values=True,
        ),
    )


def build_env_example_content(*, answers: SetupAnswers) -> str:
    return _join_env_lines(
        lines=_build_base_env_lines(
            answers=answers,
            credentials=EnvCredentials(
                jwt_key="example-jwt-key-with-at-least-32-bytes",
                postgres_key="example-postgres-key",
                redis_key="example-redis-key",
            ),
            real_values=False,
        ),
    )


def build_test_env_example_content() -> str:
    return _join_env_lines(
        lines=[
            "# Application",
            "ENVIRONMENT=test",
            "LOGGING_LEVEL=DEBUG",
            "",
            "# Secrets",
            "JWT_SECRET_KEY=test-jwt-secret-key-with-at-least-32-bytes",
            "",
            "# Observability",
            "LOGFIRE_ENABLED=false",
            "",
            "# Database",
            "DATABASE_URL=sqlite+aiosqlite:///test_db.sqlite3",
            "",
            "# Redis",
            "REDIS_URL=redis://localhost:6379/0",
        ],
    )


def _build_base_env_lines(
    *,
    answers: SetupAnswers,
    credentials: EnvCredentials,
    real_values: bool,
) -> list[str]:
    lines = [
        "# Compose",
        f"COMPOSE_PROJECT_NAME={_compose_project_name(answers=answers)}",
        "COMPOSE_FILE=docker/docker-compose.yaml:docker/docker-compose.local.yaml",
        "",
        "# Application",
        "ENVIRONMENT=local",
        "LOGGING_LEVEL=DEBUG",
        "",
        "# Secrets",
        f"JWT_SECRET_KEY={credentials.jwt_key}",
        "",
        "# HTTP",
        *_build_http_lines(answers=answers),
        "",
        "# Observability",
        f"LOGFIRE_ENABLED={str(answers.enable_logfire).lower()}",
        f"LOGFIRE_SERVICE_NAME={answers.distribution_name}",
        f"LOGFIRE_ENVIRONMENT={answers.logfire_environment or 'local'}",
    ]
    if answers.enable_logfire:
        logfire_token = (answers.logfire_token or "") if real_values else "replace-me"
        lines.append(f"LOGFIRE_TOKEN={logfire_token}")

    lines.extend(
        [
            "",
            "# Database",
            *_build_database_lines(
                answers=answers,
                credentials=credentials,
                real_values=real_values,
            ),
            "",
            "# Redis",
            *_build_redis_lines(
                answers=answers,
                credentials=credentials,
                real_values=real_values,
            ),
        ],
    )
    return lines


def _build_http_lines(*, answers: SetupAnswers) -> list[str]:
    allowed_hosts = ["127.0.0.1", "localhost", "0.0.0.0"]  # noqa: S104
    cors_allow_origins = ["http://localhost"]

    if answers.production_api_origin is not None:
        production_api_host = _host_from_origin(origin=answers.production_api_origin)
        if production_api_host is not None and production_api_host not in allowed_hosts:
            allowed_hosts.append(production_api_host)

    if answers.frontend_origin is not None:
        frontend_origin = _normalize_origin(origin=answers.frontend_origin)
        if frontend_origin not in cors_allow_origins:
            cors_allow_origins.append(frontend_origin)

    return [
        f"ALLOWED_HOSTS={_json_env_value(allowed_hosts)}",
        f"CORS_ALLOW_ORIGINS={_json_env_value(cors_allow_origins)}",
    ]


def _build_database_lines(
    *,
    answers: SetupAnswers,
    credentials: EnvCredentials,
    real_values: bool,
) -> list[str]:
    if answers.database_mode == DatabaseMode.SQLITE:
        return [
            "DATABASE_URL=sqlite+aiosqlite:///db.sqlite3",
        ]

    if answers.database_mode == DatabaseMode.REMOTE_POSTGRES:
        database_url = (
            answers.database_url
            if real_values
            else f"postgres://user:password@db.example.com:5432/{answers.package_name}"
        )
        return [
            f'DATABASE_URL="{database_url or ""}"',
        ]

    return [
        f"POSTGRES_DB={answers.package_name}",
        f"POSTGRES_PASSWORD={credentials.postgres_key}",
        f"POSTGRES_PORT={answers.postgres_port}",
        "POSTGRES_USER=postgres",
        'DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"',
    ]


def _build_redis_lines(
    *,
    answers: SetupAnswers,
    credentials: EnvCredentials,
    real_values: bool,
) -> list[str]:
    if answers.redis_mode == RedisMode.REMOTE_REDIS:
        redis_url = (
            answers.redis_url
            if real_values
            else "redis://default:password@redis.example.com:6379/0"
        )
        return [
            f'REDIS_URL="{redis_url or ""}"',
        ]

    return [
        f"REDIS_PASSWORD={credentials.redis_key}",
        f"REDIS_PORT={answers.redis_port}",
        'REDIS_URL="redis://default:${REDIS_PASSWORD}@localhost:${REDIS_PORT}/0"',
    ]


def _compose_project_name(*, answers: SetupAnswers) -> str:
    allowed_name = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in answers.distribution_name.lower()
    ).strip("-_")
    return allowed_name or answers.package_name


def _normalize_origin(*, origin: str) -> str:
    parsed = urlsplit(origin.strip())
    return f"{parsed.scheme}://{parsed.netloc}"


def _host_from_origin(*, origin: str) -> str | None:
    parsed = urlsplit(origin.strip())
    return parsed.hostname


def _json_env_value(value: list[str]) -> str:
    return dumps(value, separators=(",", ":"))


def _join_env_lines(*, lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"
