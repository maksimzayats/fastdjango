from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import questionary

from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers, StorageMode

PACKAGE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
DISTRIBUTION_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*[a-z0-9]$")
TEMPLATE_PROJECT_NAME = "fastdjango"
TEMPLATE_PACKAGE_NAME = "fastdjango"
TEMPLATE_DISTRIBUTION_NAME = "fastdjango"
TEMPLATE_REPOSITORY_URLS = frozenset(
    {
        "git@github.com:maksimzayats/fastdjango",
        "https://github.com/maksimzayats/fastdjango",
        "ssh://git@github.com/maksimzayats/fastdjango",
    },
)
MAX_PORT = 65535


@dataclass(frozen=True, kw_only=True)
class StoragePromptAnswers:
    s3_endpoint_url: str | None = None
    s3_public_endpoint_url: str | None = None
    s3_region_name: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_bucket_name: str = "public"
    s3_protected_bucket_name: str = "protected"
    minio_api_port: int = 9000
    minio_console_port: int = 9001


@dataclass(frozen=True, kw_only=True)
class DatabasePromptAnswers:
    database_url: str | None = None
    postgres_port: int = 5432


@dataclass(frozen=True, kw_only=True)
class RedisPromptAnswers:
    redis_url: str | None = None
    redis_port: int = 6379


@dataclass(frozen=True, kw_only=True)
class PublicOriginPromptAnswers:
    production_api_origin: str | None = None
    frontend_origin: str | None = None


@dataclass(frozen=True, kw_only=True)
class LogfirePromptAnswers:
    enable_logfire: bool = False
    logfire_token: str | None = None
    logfire_environment: str = "local"


@dataclass(frozen=True, kw_only=True)
class GitPromptAnswers:
    reinitialize_git_repository: bool = True
    create_initial_commit: bool = True


def prompt_for_answers(*, repo_root: Path) -> SetupAnswers:
    project_name = _ask_text(
        f"Project name (replace template default: {TEMPLATE_PROJECT_NAME})",
        validate=_validate_project_name,
    )
    suggested_package_name = _suggest_package_name(project_name=project_name)
    package_name = _ask_text(
        "Python package name (import path; edit or press Enter)",
        default=suggested_package_name,
        validate=_validate_package_name,
    )
    suggested_distribution_name = package_name.strip().replace("_", "-")
    distribution_name = _ask_text(
        "Distribution name (pyproject package and checkout folder; edit or press Enter)",
        default=suggested_distribution_name,
        validate=_validate_distribution_name,
    )
    keep_docs = _ask_confirm("Keep documentation?", default=True)
    docs_site_url = _ask_docs_site_url(keep_docs=keep_docs)
    repo_url = _ask_repo_url()
    git_answers = _ask_git_answers(repo_root=repo_root)
    storage_mode = _ask_storage_mode()
    storage_answers = _ask_storage_answers(storage_mode=storage_mode)
    database_mode = _ask_database_mode()
    database_answers = _ask_database_answers(database_mode=database_mode)
    redis_mode = _ask_redis_mode()
    redis_answers = _ask_redis_answers(redis_mode=redis_mode)
    public_origin_answers = _ask_public_origin_answers()
    logfire_answers = _ask_logfire_answers()
    delete_wizard = _ask_confirm("Delete setup wizard after setup?", default=True)
    overwrite_env = _ask_overwrite_env(repo_root=repo_root)

    return SetupAnswers(
        project_name=project_name.strip(),
        package_name=package_name.strip(),
        distribution_name=distribution_name.strip(),
        docs_site_url=docs_site_url,
        storage_mode=storage_mode,
        database_mode=database_mode,
        redis_mode=redis_mode,
        keep_docs=keep_docs,
        delete_wizard=delete_wizard,
        overwrite_env=overwrite_env,
        repo_url=repo_url,
        reinitialize_git_repository=git_answers.reinitialize_git_repository,
        create_initial_commit=git_answers.create_initial_commit,
        s3_endpoint_url=storage_answers.s3_endpoint_url,
        s3_public_endpoint_url=storage_answers.s3_public_endpoint_url,
        s3_region_name=storage_answers.s3_region_name,
        s3_access_key_id=storage_answers.s3_access_key_id,
        s3_secret_access_key=storage_answers.s3_secret_access_key,
        s3_public_bucket_name=storage_answers.s3_public_bucket_name,
        s3_protected_bucket_name=storage_answers.s3_protected_bucket_name,
        database_url=database_answers.database_url,
        redis_url=redis_answers.redis_url,
        production_api_origin=public_origin_answers.production_api_origin,
        frontend_origin=public_origin_answers.frontend_origin,
        enable_logfire=logfire_answers.enable_logfire,
        logfire_token=logfire_answers.logfire_token,
        logfire_environment=logfire_answers.logfire_environment,
        postgres_port=database_answers.postgres_port,
        redis_port=redis_answers.redis_port,
        minio_api_port=storage_answers.minio_api_port,
        minio_console_port=storage_answers.minio_console_port,
    )


def confirm_plan() -> bool:
    return _ask_confirm("Apply these changes?", default=False)


def _ask_storage_mode() -> StorageMode:
    value = questionary.select(
        "Storage mode",
        choices=[
            questionary.Choice("Local filesystem", StorageMode.LOCAL),
            questionary.Choice("Local MinIO", StorageMode.MINIO),
            questionary.Choice("Remote S3-compatible", StorageMode.REMOTE_S3),
        ],
        default=StorageMode.LOCAL,
    ).ask()
    if value is None:
        raise KeyboardInterrupt

    return cast(StorageMode, value)


def _ask_database_mode() -> DatabaseMode:
    value = questionary.select(
        "Database",
        choices=[
            questionary.Choice("Local Docker PostgreSQL", DatabaseMode.DOCKER_POSTGRES),
            questionary.Choice("Local SQLite", DatabaseMode.SQLITE),
            questionary.Choice("Remote PostgreSQL", DatabaseMode.REMOTE_POSTGRES),
        ],
        default=DatabaseMode.DOCKER_POSTGRES,
    ).ask()
    if value is None:
        raise KeyboardInterrupt

    return cast(DatabaseMode, value)


def _ask_database_answers(*, database_mode: DatabaseMode) -> DatabasePromptAnswers:
    if database_mode == DatabaseMode.DOCKER_POSTGRES:
        return DatabasePromptAnswers(
            postgres_port=_ask_int("PostgreSQL host port", default=5432),
        )

    if database_mode != DatabaseMode.REMOTE_POSTGRES:
        return DatabasePromptAnswers()

    return DatabasePromptAnswers(
        database_url=_ask_text(
            "Database URL (example: postgres://user:password@db.example.com:5432/app)",
            validate=_validate_required_text,
        ),
    )


def _ask_redis_mode() -> RedisMode:
    value = questionary.select(
        "Redis",
        choices=[
            questionary.Choice("Local Docker Redis", RedisMode.DOCKER_REDIS),
            questionary.Choice("Remote Redis", RedisMode.REMOTE_REDIS),
        ],
        default=RedisMode.DOCKER_REDIS,
    ).ask()
    if value is None:
        raise KeyboardInterrupt

    return cast(RedisMode, value)


def _ask_redis_answers(*, redis_mode: RedisMode) -> RedisPromptAnswers:
    if redis_mode == RedisMode.REMOTE_REDIS:
        return RedisPromptAnswers(
            redis_url=_ask_text(
                "Redis URL (example: redis://default:password@redis.example.com:6379/0)",
                validate=_validate_required_text,
            ),
        )

    return RedisPromptAnswers(
        redis_port=_ask_int("Redis host port", default=6379),
    )


def _ask_storage_answers(*, storage_mode: StorageMode) -> StoragePromptAnswers:
    if storage_mode == StorageMode.MINIO:
        return StoragePromptAnswers(
            minio_api_port=_ask_int("MinIO API host port", default=9000),
            minio_console_port=_ask_int("MinIO console host port", default=9001),
        )

    if storage_mode != StorageMode.REMOTE_S3:
        return StoragePromptAnswers()

    return StoragePromptAnswers(
        s3_endpoint_url=_ask_text(
            "S3 endpoint URL (example: https://s3.example.com)",
            validate=_validate_required_text,
        ),
        s3_public_endpoint_url=_ask_text(
            "Public S3 endpoint URL (example: https://cdn.example.com)",
            validate=_validate_required_text,
        ),
        s3_region_name=_ask_text(
            "S3 region (example: us-east-1)",
            validate=_validate_required_text,
        ),
        s3_access_key_id=_ask_text("S3 access key ID", validate=_validate_required_text),
        s3_secret_access_key=_ask_text("S3 secret access key", validate=_validate_required_text),
        s3_public_bucket_name=_optional_text("Public bucket (blank uses: public)") or "public",
        s3_protected_bucket_name=_optional_text("Protected bucket (blank uses: protected)")
        or "protected",
    )


def _ask_docs_site_url(*, keep_docs: bool) -> str | None:
    if not keep_docs:
        return None

    return _optional_text(
        "Docs site URL (optional; blank keeps docs local-only for now)",
        validate=_validate_optional_http_url,
    )


def _ask_repo_url() -> str | None:
    return _optional_text(
        "Repository URL (HTTP(S), optional; used for docs metadata and, if Git is reinitialized, as Git origin; blank removes template repository links)",
        validate=_validate_optional_http_url,
    )


def _ask_git_answers(*, repo_root: Path | None = None) -> GitPromptAnswers:
    reinitialize_git_repository = _ask_confirm(
        "Reinitialize Git repository to remove cloned-template history and old origin?",
        default=_default_reinitialize_git_repository(repo_root=repo_root),
    )

    return GitPromptAnswers(
        reinitialize_git_repository=reinitialize_git_repository,
        create_initial_commit=_ask_confirm("Create initial commit?", default=True),
    )


def _default_reinitialize_git_repository(*, repo_root: Path | None) -> bool:
    if repo_root is None:
        return True

    if not (repo_root / ".git").exists():
        return True

    origin_url = _current_origin_url(repo_root=repo_root)
    if origin_url is None:
        return False

    normalized_origin_url = origin_url.casefold().removesuffix(".git").rstrip("/")
    return normalized_origin_url in TEMPLATE_REPOSITORY_URLS


def _current_origin_url(*, repo_root: Path) -> str | None:
    if not (repo_root / ".git").exists():
        return None

    git_path = shutil.which("git")
    if git_path is None:
        return None

    result = subprocess.run(  # noqa: S603
        [git_path, "config", "--get", "remote.origin.url"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() or None


def _ask_public_origin_answers() -> PublicOriginPromptAnswers:
    return PublicOriginPromptAnswers(
        production_api_origin=_optional_text(
            "Production API origin (optional; blank keeps localhost-only trusted hosts)",
            validate=_validate_optional_origin,
        ),
        frontend_origin=_optional_text(
            "Frontend origin (optional; blank skips generated CORS origin)",
            validate=_validate_optional_origin,
        ),
    )


def _ask_logfire_answers() -> LogfirePromptAnswers:
    enable_logfire = _ask_confirm("Enable Logfire observability?", default=False)
    if not enable_logfire:
        return LogfirePromptAnswers()

    return LogfirePromptAnswers(
        enable_logfire=True,
        logfire_token=_ask_text("Logfire token", validate=_validate_required_text),
        logfire_environment=_ask_text(
            "Logfire environment (blank uses: local)",
            default="local",
        )
        or "local",
    )


def _ask_overwrite_env(*, repo_root: Path) -> bool:
    if not (repo_root / ".env").exists():
        return True

    return _ask_confirm("Overwrite existing .env?", default=False)


def _ask_text(
    message: str,
    *,
    default: str = "",
    validate: QuestionaryValidator | None = None,
) -> str:
    value = questionary.text(message, default=default, validate=validate).ask()
    if value is None:
        raise KeyboardInterrupt

    return value


def _optional_text(
    message: str,
    *,
    validate: QuestionaryValidator | None = None,
) -> str | None:
    value = _ask_text(message, default="", validate=validate)
    value = value.strip()
    return value or None


def _ask_int(message: str, *, default: int) -> int:
    value = _ask_text(message, default=str(default), validate=_validate_port)
    return int(value.strip() or default)


def _ask_confirm(message: str, *, default: bool) -> bool:
    value = questionary.confirm(message, default=default).ask()
    if value is None:
        raise KeyboardInterrupt

    return bool(value)


def _validate_package_name(value: str) -> bool | str:
    value = value.strip()
    if value == TEMPLATE_PACKAGE_NAME:
        return "Replace the template package name with your own package name."

    if PACKAGE_NAME_PATTERN.fullmatch(value):
        return True

    return "Use a valid lowercase Python package name, like my_api."


def _validate_distribution_name(value: str) -> bool | str:
    value = value.strip()
    if value == TEMPLATE_DISTRIBUTION_NAME:
        return "Replace the template distribution name with your own distribution name."

    if DISTRIBUTION_NAME_PATTERN.fullmatch(value):
        return True

    return "Use a valid package distribution name, like my-api."


def _validate_project_name(value: str) -> bool | str:
    value = value.strip()
    if not value:
        return "Project name is required."

    if _normalized_name(value) == _normalized_name(TEMPLATE_PROJECT_NAME):
        return "Replace the template project name with your own project name."

    return True


def _validate_required_text(value: str) -> bool | str:
    if value.strip():
        return True

    return "This value is required."


def _validate_optional_origin(value: str) -> bool | str:
    value = value.strip()
    if not value:
        return True

    if re.fullmatch(r"https?://[^/\s]+", value):
        return True

    return "Use an origin like https://api.example.com without a path."


def _validate_optional_url(value: str) -> bool | str:
    value = value.strip()
    if not value:
        return True

    if re.fullmatch(r"https?://[^/\s]+(?:/[^ \t]*)?", value):
        return True

    if re.fullmatch(r"git@[^:\s]+:[^/\s]+/[^/\s]+(?:\.git)?", value):
        return True

    return "Use a URL like https://example.com or git@github.com:owner/repo.git."


def _validate_optional_http_url(value: str) -> bool | str:
    value = value.strip()
    if not value:
        return True

    if re.fullmatch(r"https?://[^/\s]+(?:/[^ \t]*)?", value):
        return True

    return "Use a URL like https://example.com."


def _validate_port(value: str) -> bool | str:
    value = value.strip()
    if not value:
        return True

    try:
        port = int(value)
    except ValueError:
        return "Use a number between 1 and 65535."

    if 1 <= port <= MAX_PORT:
        return True

    return "Use a number between 1 and 65535."


def _suggest_package_name(*, project_name: str) -> str:
    normalized = project_name.strip().casefold().replace(" ", "")
    package_name = re.sub(pattern=r"[^a-z0-9_]", repl="", string=normalized).lstrip("_")
    if not package_name:
        return ""

    if not package_name[0].isalpha():
        return f"app{package_name}"

    return package_name


def _normalized_name(value: str) -> str:
    return re.sub(pattern=r"[^a-z0-9]", repl="", string=value.casefold())


type QuestionaryValidator = Callable[[str], bool | str]
