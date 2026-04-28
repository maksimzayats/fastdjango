from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import yaml

from tests.architecture._source import REPO_ROOT

COMPOSE_FILE_NAMES = {
    "docker-compose.local.yaml",
    "docker-compose.test.yaml",
    "docker-compose.yaml",
}
HEALTHCHECK_REQUIRED_SERVICES = {
    "api",
    "minio",
    "pgbouncer",
    "postgres",
    "redis",
}
HEALTHCHECK_COMMAND_TYPES = {"CMD", "CMD-SHELL", "NONE"}
EXCLUDED_TOP_LEVEL_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "venv",
}
DOCKERFILE_REQUIRED_IGNORES = {
    ".agents/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "build/",
    "dist/",
    "docs/",
    "htmlcov/",
    "management/setup_wizard/",
    "site/",
    "tests/",
}


def test_docker_assets_stay_in_docker_directory() -> None:
    violations = [
        str(path.relative_to(REPO_ROOT))
        for path in _iter_repo_files()
        if _is_docker_asset(path)
        if path.relative_to(REPO_ROOT).parts[0] != "docker"
    ]

    assert violations == [], "Docker assets must live under docker/."


def test_compose_files_are_known_and_parseable() -> None:
    compose_configs = {path.name: _load_yaml(path) for path in _iter_compose_files()}

    assert set(compose_configs) == COMPOSE_FILE_NAMES


def test_dockerfile_uses_uv_cache_friendly_multistage_build() -> None:
    dockerfile = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("# syntax=docker/dockerfile:")
    assert "FROM ghcr.io/astral-sh/uv:" in dockerfile
    assert dockerfile.count("FROM python:") == 2
    assert "--mount=type=cache,target=/root/.cache/uv" in dockerfile
    assert "--mount=type=bind,source=uv.lock,target=uv.lock,readonly" in dockerfile
    assert "--mount=type=bind,source=pyproject.toml,target=pyproject.toml,readonly" in dockerfile
    assert "uv sync --locked --no-install-project" in dockerfile
    assert "COPY . /app" not in dockerfile
    assert "COPY --from=builder --chown=app:app /app/.venv /app/.venv" in dockerfile
    assert "COPY --from=builder --chown=app:app /app/src /app/src" in dockerfile
    assert "USER app" in dockerfile
    assert dockerfile.index("uv sync --locked --no-install-project") < dockerfile.index(
        "COPY src ./src",
    )


def test_dockerfile_ignore_excludes_high_churn_non_runtime_paths() -> None:
    dockerignore = _dockerignore_entries()
    missing_entries = sorted(DOCKERFILE_REQUIRED_IGNORES - dockerignore)

    assert missing_entries == []


def test_runtime_compose_services_have_healthchecks() -> None:
    compose = _compose_config("docker-compose.yaml")
    services = _services(compose)
    violations = [
        service_name
        for service_name in sorted(HEALTHCHECK_REQUIRED_SERVICES)
        if "healthcheck" not in services.get(service_name, {})
    ]

    assert violations == [], "Long-running runtime services must define healthchecks."


def test_compose_healthchecks_use_valid_command_form() -> None:
    violations = [
        f"{compose_path.name}:{service_name}"
        for compose_path in _iter_compose_files()
        for service_name, service in _services(_load_yaml(compose_path)).items()
        if (healthcheck := service.get("healthcheck")) is not None
        if not _is_valid_healthcheck_test(healthcheck.get("test"))
    ]

    assert violations == [], (
        "Compose healthcheck.test must be a command string or a list starting with "
        "CMD, CMD-SHELL, or NONE."
    )


def test_healthchecked_compose_dependencies_wait_until_healthy() -> None:
    compose = _compose_config("docker-compose.yaml")
    services = _services(compose)
    healthchecked_services = {
        service_name for service_name, service in services.items() if "healthcheck" in service
    }
    violations = [
        f"{service_name}->{dependency_name}"
        for service_name, service in services.items()
        for dependency_name, dependency in _dependency_items(service)
        if dependency_name in healthchecked_services
        if dependency.get("condition") != "service_healthy"
    ]

    assert violations == [], (
        "Services depending on healthchecked services must use condition: service_healthy."
    )


def _iter_compose_files() -> list[Path]:
    return sorted((REPO_ROOT / "docker").glob("docker-compose*.yaml"))


def _iter_repo_files() -> Iterable[Path]:
    for entry in sorted(REPO_ROOT.iterdir()):
        if entry.name in EXCLUDED_TOP_LEVEL_DIRS:
            continue

        if entry.is_file():
            yield entry
            continue

        yield from (path for path in entry.rglob("*") if path.is_file())


def _compose_config(file_name: str) -> dict[str, Any]:
    return _load_yaml(REPO_ROOT / "docker" / file_name)


def _load_yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def _dockerignore_entries() -> set[str]:
    dockerignore_path = REPO_ROOT / "docker" / "Dockerfile.dockerignore"
    return {
        line.strip()
        for line in dockerignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def _services(compose: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], compose.get("services", {}))


def _dependency_items(service: dict[str, Any]) -> list[tuple[str, dict[str, str]]]:
    depends_on = service.get("depends_on", {})

    if not isinstance(depends_on, dict):
        return []

    return [
        (dependency_name, dependency)
        for dependency_name, dependency in depends_on.items()
        if isinstance(dependency, dict)
    ]


def _is_valid_healthcheck_test(test: object) -> bool:
    if isinstance(test, str):
        return bool(test)

    return (
        isinstance(test, list)
        and bool(test)
        and isinstance(test[0], str)
        and test[0] in HEALTHCHECK_COMMAND_TYPES
    )


def _is_docker_asset(path: Path) -> bool:
    return path.name.startswith("Dockerfile") or path.name.startswith("docker-compose")
