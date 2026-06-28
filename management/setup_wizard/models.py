from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal


class DatabaseMode(StrEnum):
    SQLITE = "sqlite"
    DOCKER_POSTGRES = "docker-postgres"
    REMOTE_POSTGRES = "remote-postgres"


class RedisMode(StrEnum):
    DOCKER_REDIS = "docker-redis"
    REMOTE_REDIS = "remote-redis"


@dataclass(frozen=True, kw_only=True)
class SetupAnswers:
    project_name: str
    package_name: str
    distribution_name: str
    docs_site_url: str | None
    database_mode: DatabaseMode
    redis_mode: RedisMode
    keep_docs: bool
    delete_wizard: bool
    overwrite_env: bool

    repo_url: str | None = None
    reinitialize_git_repository: bool = True
    create_initial_commit: bool = True
    production_api_origin: str | None = None
    frontend_origin: str | None = None
    database_url: str | None = None
    redis_url: str | None = None
    enable_logfire: bool = False
    logfire_token: str | None = None
    logfire_environment: str = "local"
    postgres_port: int = 5432
    redis_port: int = 6379


@dataclass(frozen=True, kw_only=True)
class FileOperation:
    kind: Literal["write", "delete", "rename", "command"]
    path: Path
    detail: str
    target_path: Path | None = None
    content: str | None = None
    command: tuple[str, ...] | None = None
