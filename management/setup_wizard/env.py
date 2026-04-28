from __future__ import annotations

import secrets
from dataclasses import dataclass
from json import dumps
from urllib.parse import urlsplit

from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers, StorageMode


@dataclass(frozen=True, kw_only=True)
class EnvCredentials:
    django_key: str
    jwt_key: str
    postgres_key: str
    redis_key: str


def build_env_content(*, answers: SetupAnswers) -> str:
    lines = _build_base_env_lines(
        answers=answers,
        credentials=EnvCredentials(
            django_key=secrets.token_urlsafe(48),
            jwt_key=secrets.token_urlsafe(48),
            postgres_key=secrets.token_urlsafe(32),
            redis_key=secrets.token_urlsafe(32),
        ),
        real_values=True,
    )
    lines.extend(_build_storage_lines(answers=answers, real_values=True))
    return _join_env_lines(lines=lines)


def build_env_example_content(*, answers: SetupAnswers) -> str:
    lines = _build_base_env_lines(
        answers=answers,
        credentials=EnvCredentials(
            django_key="example-django-key",
            jwt_key="example-jwt-key-with-at-least-32-bytes",
            postgres_key="example-postgres-key",
            redis_key="example-redis-key",
        ),
        real_values=False,
    )
    lines.extend(_build_storage_lines(answers=answers, real_values=False))
    return _join_env_lines(lines=lines)


def build_test_env_example_content() -> str:
    return _join_env_lines(
        lines=[
            "# Test environment specific overrides",
            "ENVIRONMENT=test",
            "DJANGO_DEBUG=true",
            "DJANGO_SECRET_KEY=test-django-secret-key",
            "JWT_SECRET_KEY=test-jwt-secret-key-with-at-least-32-bytes",
            "LOGGING_LEVEL=DEBUG",
            "LOGFIRE_ENABLED=false",
            "DATABASE_TEST_NAME=test_db.sqlite3",
            "DATABASE_URL=sqlite:///test_db.sqlite3",
            "REDIS_URL=redis://localhost:6379/0",
            "",
            "STORAGE_BACKEND=local",
        ],
    )


def _build_base_env_lines(
    *,
    answers: SetupAnswers,
    credentials: EnvCredentials,
    real_values: bool,
) -> list[str]:
    lines = [
        f"COMPOSE_PROJECT_NAME={_compose_project_name(answers=answers)}",
        "COMPOSE_FILE=docker/docker-compose.yaml:docker/docker-compose.local.yaml",
        "",
        f"DJANGO_SECRET_KEY={credentials.django_key}",
        f"JWT_SECRET_KEY={credentials.jwt_key}",
        "",
        "ENVIRONMENT=local",
        "DJANGO_DEBUG=true",
        "LOGGING_LEVEL=DEBUG",
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
            *(_build_http_lines(answers=answers)),
            "",
            *(
                _build_database_lines(
                    answers=answers,
                    credentials=credentials,
                    real_values=real_values,
                )
            ),
            "",
            *(
                _build_redis_lines(
                    answers=answers,
                    credentials=credentials,
                    real_values=real_values,
                )
            ),
            "",
        ],
    )
    return lines


def _build_http_lines(*, answers: SetupAnswers) -> list[str]:
    allowed_hosts = ["127.0.0.1", "localhost", "0.0.0.0"]  # noqa: S104
    csrf_trusted_origins = ["http://localhost"]
    cors_allow_origins = ["http://localhost"]

    for origin in (answers.production_api_origin, answers.frontend_origin):
        if origin is None:
            continue

        normalized_origin = _normalize_origin(origin=origin)
        if normalized_origin not in csrf_trusted_origins:
            csrf_trusted_origins.append(normalized_origin)

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
        f"CSRF_TRUSTED_ORIGINS={_json_env_value(csrf_trusted_origins)}",
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
            "DATABASE_URL=sqlite:///db.sqlite3",
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
        "POSTGRES_USER=postgres",
        f"POSTGRES_DB={answers.package_name}",
        f"POSTGRES_PASSWORD={credentials.postgres_key}",
        f"POSTGRES_PORT={answers.postgres_port}",
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


def _build_storage_lines(*, answers: SetupAnswers, real_values: bool) -> list[str]:
    if answers.storage_mode == StorageMode.LOCAL:
        return ["STORAGE_BACKEND=local"]

    if answers.storage_mode == StorageMode.MINIO:
        return [
            f"MINIO_API_PORT={answers.minio_api_port}",
            f"MINIO_CONSOLE_PORT={answers.minio_console_port}",
            "STORAGE_BACKEND=s3",
            f"AWS_S3_ENDPOINT_URL=http://localhost:{answers.minio_api_port}",
            f"AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:{answers.minio_api_port}",
            "AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id",
            "AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key",
            "AWS_S3_REGION_NAME=us-east-1",
            "AWS_S3_PUBLIC_BUCKET_NAME=public",
            "AWS_S3_PROTECTED_BUCKET_NAME=protected",
        ]

    if real_values:
        return [
            "STORAGE_BACKEND=s3",
            f"AWS_S3_ENDPOINT_URL={answers.s3_endpoint_url or ''}",
            f"AWS_S3_PUBLIC_ENDPOINT_URL={answers.s3_public_endpoint_url or ''}",
            f"AWS_S3_ACCESS_KEY_ID={answers.s3_access_key_id or ''}",
            f"AWS_S3_SECRET_ACCESS_KEY={answers.s3_secret_access_key or ''}",
            f"AWS_S3_REGION_NAME={answers.s3_region_name or ''}",
            f"AWS_S3_PUBLIC_BUCKET_NAME={answers.s3_public_bucket_name}",
            f"AWS_S3_PROTECTED_BUCKET_NAME={answers.s3_protected_bucket_name}",
        ]

    return [
        "STORAGE_BACKEND=s3",
        "AWS_S3_ENDPOINT_URL=https://s3.example.com",
        "AWS_S3_PUBLIC_ENDPOINT_URL=https://cdn.example.com",
        "AWS_S3_ACCESS_KEY_ID=replace-me",
        "AWS_S3_SECRET_ACCESS_KEY=replace-me",
        "AWS_S3_REGION_NAME=us-east-1",
        "AWS_S3_PUBLIC_BUCKET_NAME=public",
        "AWS_S3_PROTECTED_BUCKET_NAME=protected",
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
