from __future__ import annotations

import secrets
from dataclasses import dataclass
from json import dumps
from urllib.parse import urlsplit

from management.setup_wizard.models import (
    AuthenticationMode,
    DatabaseMode,
    RedisMode,
    SetupAnswers,
    StorageMode,
)


@dataclass(frozen=True, kw_only=True)
class EnvCredentials:
    django_key: str
    jwt_key: str
    static_api_key: str
    postgres_key: str
    redis_key: str


def build_env_content(*, answers: SetupAnswers) -> str:
    lines = _build_base_env_lines(
        answers=answers,
        credentials=EnvCredentials(
            django_key=secrets.token_urlsafe(48),
            jwt_key=secrets.token_urlsafe(48),
            static_api_key=secrets.token_urlsafe(32),
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
            static_api_key="example-static-api-key",
            postgres_key="example-postgres-key",
            redis_key="example-redis-key",
        ),
        real_values=False,
    )
    lines.extend(_build_storage_lines(answers=answers, real_values=False))
    return _join_env_lines(lines=lines)


def build_test_env_example_content(
    *,
    answers: SetupAnswers | None = None,
) -> str:
    authentication_mode = (
        answers.authentication_mode
        if answers is not None
        else AuthenticationMode.JWT_REFRESH_SESSION
    )

    return _join_env_lines(
        lines=[
            "# Application",
            "DJANGO_DEBUG=true",
            "ENVIRONMENT=test",
            "LOGGING_LEVEL=DEBUG",
            "",
            "# Secrets",
            "DJANGO_SECRET_KEY=test-django-secret-key",
            "",
            "# Authentication",
            *_build_authentication_lines(
                authentication_mode=authentication_mode,
                jwt_key="test-jwt-secret-key-with-at-least-32-bytes",
                static_api_key="test-static-api-key",
            ),
            "",
            "# Observability",
            "LOGFIRE_ENABLED=false",
            "",
            "# Database",
            "DATABASE_TEST_NAME=test_db.sqlite3",
            "DATABASE_URL=sqlite:///test_db.sqlite3",
            "",
            "# Redis",
            "REDIS_URL=redis://localhost:6379/0",
            "",
            "# Storage",
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
        "# Compose",
        f"COMPOSE_PROJECT_NAME={_compose_project_name(answers=answers)}",
        "COMPOSE_FILE=docker/docker-compose.yaml:docker/docker-compose.local.yaml",
        "",
        "# Application",
        "DJANGO_DEBUG=true",
        "ENVIRONMENT=local",
        "LOGGING_LEVEL=DEBUG",
        "",
        "# Secrets",
        f"DJANGO_SECRET_KEY={credentials.django_key}",
        "",
        "# Authentication",
        *(
            _build_authentication_lines(
                authentication_mode=answers.authentication_mode,
                jwt_key=credentials.jwt_key,
                static_api_key=credentials.static_api_key,
            )
        ),
        "",
        "# HTTP",
        *(_build_http_lines(answers=answers)),
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
            *(
                _build_database_lines(
                    answers=answers,
                    credentials=credentials,
                    real_values=real_values,
                )
            ),
            "",
            "# Redis",
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


def _build_authentication_lines(
    *,
    authentication_mode: AuthenticationMode,
    jwt_key: str,
    static_api_key: str,
) -> list[str]:
    lines = [f"AUTHENTICATION_MODE={authentication_mode.value}"]
    if authentication_mode == AuthenticationMode.JWT_REFRESH_SESSION:
        lines.append(f"JWT_SECRET_KEY={jwt_key}")
        return lines

    if authentication_mode == AuthenticationMode.STATIC_API_KEYS:
        lines.append(
            f"STATIC_API_KEYS={_static_api_keys_env_value(api_key=static_api_key)}",
        )

    return lines


def _static_api_keys_env_value(*, api_key: str) -> str:
    return dumps(
        {
            api_key: {
                "id": 1,
                "username": "local-api-key",
                "email": "local-api-key@example.com",
                "first_name": "Local",
                "last_name": "API Key",
                "is_staff": True,
                "is_superuser": False,
            },
        },
        separators=(",", ":"),
    )


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


def _build_storage_lines(*, answers: SetupAnswers, real_values: bool) -> list[str]:
    if answers.storage_mode == StorageMode.LOCAL:
        return [
            "# Storage",
            "STORAGE_BACKEND=local",
        ]

    if answers.storage_mode == StorageMode.MINIO:
        minio_access_key = (
            f"fd{secrets.token_hex(9)}" if real_values else "example-minio-access-key-id"
        )
        minio_secret_key = (
            secrets.token_urlsafe(40) if real_values else "example-minio-secret-access-key"
        )
        return [
            "# Storage",
            "STORAGE_BACKEND=s3",
            f"MINIO_API_PORT={answers.minio_api_port}",
            f"MINIO_CONSOLE_PORT={answers.minio_console_port}",
            f"MINIO_ROOT_USER={minio_access_key}",
            f"MINIO_ROOT_PASSWORD={minio_secret_key}",
            "",
            "# S3",
            "AWS_S3_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}",
            "AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}",
            f"AWS_S3_ACCESS_KEY_ID={minio_access_key}",
            f"AWS_S3_SECRET_ACCESS_KEY={minio_secret_key}",
            "AWS_S3_REGION_NAME=us-east-1",
            "AWS_S3_PUBLIC_BUCKET_NAME=public",
            "AWS_S3_PROTECTED_BUCKET_NAME=protected",
        ]

    if real_values:
        return [
            "# Storage",
            "STORAGE_BACKEND=s3",
            "",
            "# S3",
            f"AWS_S3_ENDPOINT_URL={answers.s3_endpoint_url or ''}",
            f"AWS_S3_PUBLIC_ENDPOINT_URL={answers.s3_public_endpoint_url or ''}",
            f"AWS_S3_ACCESS_KEY_ID={answers.s3_access_key_id or ''}",
            f"AWS_S3_SECRET_ACCESS_KEY={answers.s3_secret_access_key or ''}",
            f"AWS_S3_REGION_NAME={answers.s3_region_name or ''}",
            f"AWS_S3_PUBLIC_BUCKET_NAME={answers.s3_public_bucket_name}",
            f"AWS_S3_PROTECTED_BUCKET_NAME={answers.s3_protected_bucket_name}",
        ]

    return [
        "# Storage",
        "STORAGE_BACKEND=s3",
        "",
        "# S3",
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
