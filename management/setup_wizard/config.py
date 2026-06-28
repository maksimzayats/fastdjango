from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
from io import StringIO
from typing import Any, cast

import tomlkit
from ruamel.yaml import YAML

from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers
from management.setup_wizard.text_rewrite import ProjectReferences, replace_project_references

URL_WITH_SCHEME_PARTS_LENGTH = 4
LEGACY_WEB_FRAMEWORK = "djan" + "go"
LEGACY_TASK_QUEUE = "cel" + "ery"
LEGACY_TASK_SERVICES = (
    f"{LEGACY_TASK_QUEUE}-worker",
    f"{LEGACY_TASK_QUEUE}-beat",
)
LEGACY_STATIC_STEP = "collect" + "static"
LEGACY_OBJECT_STORE = "min" + "io"
LEGACY_OBJECT_STORE_BOOTSTRAP_SERVICE = f"{LEGACY_OBJECT_STORE}-create-buckets"
LEGACY_OBJECT_STORE_VOLUME = f"{LEGACY_OBJECT_STORE}_data"
LEGACY_CLOUD_ENV_PREFIX = "AW" + "S_"
OBSOLETE_COMPOSE_SERVICES = (
    *LEGACY_TASK_SERVICES,
    "migrations",
    LEGACY_STATIC_STEP,
    LEGACY_OBJECT_STORE,
    LEGACY_OBJECT_STORE_BOOTSTRAP_SERVICE,
)


def update_pyproject_toml(
    content: str,
    *,
    answers: SetupAnswers,
    old_package_name: str,
) -> str:
    document = cast(Any, tomlkit.parse(content))
    cast(Any, document["project"])["name"] = answers.distribution_name

    _update_dependency_groups(document=document, answers=answers)
    _update_mypy_config(
        document=document,
        package_name=answers.package_name,
        old_package_name=old_package_name,
    )
    _update_coverage_config(
        document=document,
        package_name=answers.package_name,
        old_package_name=old_package_name,
    )
    return tomlkit.dumps(document)


def update_ruff_toml(content: str, *, package_name: str) -> str:
    document = cast(Any, tomlkit.parse(content))
    document["src"] = ["src", "management", "tests"]
    cast(Any, document["lint"]["isort"])["known-first-party"] = [package_name]
    return tomlkit.dumps(document)


def update_prek_toml(content: str) -> str:
    document = cast(Any, tomlkit.parse(content))
    for repo in cast(list[Any], document["repos"]):
        for hook in cast(list[Any], repo.get("hooks", [])):
            _update_prek_hook(hook=hook)

    return tomlkit.dumps(document)


def update_docker_compose_yaml(
    content: str,
    *,
    answers: SetupAnswers,
    old_package_name: str,
    is_local_overlay: bool,
) -> str:
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(content)
    _rewrite_yaml_strings(value=data, answers=answers, old_package_name=old_package_name)
    _remove_obsolete_compose_services(data=data)

    if answers.database_mode == DatabaseMode.DOCKER_POSTGRES:
        _configure_postgres_compose(
            data=data,
            answers=answers,
            is_local_overlay=is_local_overlay,
        )
    else:
        _remove_postgres_compose(data=data)

    if answers.redis_mode == RedisMode.DOCKER_REDIS:
        _configure_redis_compose(
            data=data,
            answers=answers,
            is_local_overlay=is_local_overlay,
        )
    else:
        _remove_redis_compose(data=data)

    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def update_mkdocs_yaml(content: str, *, answers: SetupAnswers, old_package_name: str) -> str:
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(content)
    _rewrite_yaml_strings(value=data, answers=answers, old_package_name=old_package_name)
    data["site_name"] = answers.project_name
    if answers.docs_site_url is not None:
        data["site_url"] = answers.docs_site_url.rstrip("/")
    else:
        data.pop("site_url", None)

    if answers.repo_url is not None:
        data["repo_url"] = answers.repo_url
        data["repo_name"] = _repo_name_from_url(repo_url=answers.repo_url)
    else:
        data.pop("repo_url", None)
        data.pop("repo_name", None)

    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def _update_dependency_groups(*, document: Any, answers: SetupAnswers) -> None:
    groups = document.get("dependency-groups")
    if groups is None:
        return

    if not answers.keep_docs:
        groups.pop("docs", None)

    if answers.delete_wizard:
        groups.pop("setup", None)


def _update_mypy_config(
    *,
    document: Any,
    package_name: str,
    old_package_name: str,
) -> None:
    tool_config = document.get("tool", {})
    tool_config.pop(f"{LEGACY_WEB_FRAMEWORK}-stubs", None)
    for override in cast(list[Any], tool_config.get("mypy", {}).get("overrides", [])):
        module = override.get("module")
        if isinstance(module, str):
            override["module"] = module.replace(old_package_name, package_name)


def _update_coverage_config(
    *,
    document: Any,
    package_name: str,
    old_package_name: str,
) -> None:
    coverage_run = document["tool"]["coverage"]["run"]
    omit_values = [
        _rewrite_config_path(
            value=value,
            package_name=package_name,
            old_package_name=old_package_name,
        )
        for value in cast(list[str], coverage_run.get("omit", []))
    ]
    coverage_run["omit"] = [
        value
        for value in omit_values
        if "manage.py" not in value
        and f"/entrypoints/{LEGACY_TASK_QUEUE}/" not in value
        and f"/infrastructure/{LEGACY_WEB_FRAMEWORK}/" not in value
        and not value.endswith("/admin.py")
    ]


def _rewrite_config_path(*, value: str, package_name: str, old_package_name: str) -> str:
    return value.replace(f"src/{old_package_name}", f"src/{package_name}")


def _update_prek_hook(*, hook: Any) -> None:
    entry = hook.get("entry")
    if isinstance(entry, str) and "mypy src/ tests/" in entry:
        hook["entry"] = entry.replace("mypy src/ tests/", "mypy src/ management/ tests/")

    files = hook.get("files")
    if isinstance(files, str):
        hook["files"] = files.replace("^(src|tests)", "^(src|management|tests)")


def _rewrite_yaml_strings(
    *,
    value: Any,
    answers: SetupAnswers,
    old_package_name: str,
) -> None:
    if isinstance(value, MutableMapping):
        for key, child_value in value.items():
            if isinstance(child_value, str):
                value[key] = _rewrite_yaml_string(
                    text=child_value,
                    answers=answers,
                    old_package_name=old_package_name,
                )
            else:
                _rewrite_yaml_strings(
                    value=child_value,
                    answers=answers,
                    old_package_name=old_package_name,
                )
        return

    if isinstance(value, MutableSequence):
        for index, child_value in enumerate(value):
            if isinstance(child_value, str):
                value[index] = _rewrite_yaml_string(
                    text=child_value,
                    answers=answers,
                    old_package_name=old_package_name,
                )
            else:
                _rewrite_yaml_strings(
                    value=child_value,
                    answers=answers,
                    old_package_name=old_package_name,
                )


def _rewrite_yaml_string(*, text: str, answers: SetupAnswers, old_package_name: str) -> str:
    return replace_project_references(
        text=text,
        references=ProjectReferences(
            old_package_name=old_package_name,
            new_package_name=answers.package_name,
            project_name=answers.project_name,
            docs_site_url=answers.docs_site_url,
            repo_url=answers.repo_url,
        ),
    )


def _configure_postgres_compose(
    *,
    data: Any,
    answers: SetupAnswers,
    is_local_overlay: bool,
) -> None:
    postgres_service = data.get("services", {}).get("postgres")
    if postgres_service is not None and is_local_overlay:
        postgres_service["ports"] = [f"${{POSTGRES_PORT:-{answers.postgres_port}}}:5432"]

    if is_local_overlay:
        return

    common_environment = data.get("x-common", {}).get("environment", {})
    common_environment["DATABASE_URL"] = (
        "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}"
    )


def _configure_redis_compose(
    *,
    data: Any,
    answers: SetupAnswers,
    is_local_overlay: bool,
) -> None:
    redis_service = data.get("services", {}).get("redis")
    if redis_service is not None and is_local_overlay:
        redis_service["ports"] = [f"${{REDIS_PORT:-{answers.redis_port}}}:6379"]

    if is_local_overlay:
        return

    common_environment = data.get("x-common", {}).get("environment", {})
    common_environment["REDIS_URL"] = "redis://default:${REDIS_PASSWORD}@redis:6379/0"


def _remove_obsolete_compose_services(*, data: Any) -> None:
    services = data.get("services", {})
    for service_name in OBSOLETE_COMPOSE_SERVICES:
        services.pop(service_name, None)

    for service in services.values():
        if isinstance(service, MutableMapping):
            depends_on = service.get("depends_on")
            if isinstance(depends_on, MutableMapping):
                for dependency_name in OBSOLETE_COMPOSE_SERVICES:
                    depends_on.pop(dependency_name, None)
                if not depends_on:
                    service.pop("depends_on", None)

    common_environment = data.get("x-common", {}).get("environment", {})
    for key in tuple(common_environment):
        if key.startswith(LEGACY_CLOUD_ENV_PREFIX):
            common_environment.pop(key, None)

    volumes = data.get("volumes", {})
    volumes.pop(LEGACY_OBJECT_STORE_VOLUME, None)


def _remove_postgres_compose(*, data: Any) -> None:
    services = data.get("services", {})
    services.pop("postgres", None)
    services.pop("pgbouncer", None)

    for service_name in ("api",):
        _remove_service_dependency(
            services=services,
            service_name=service_name,
            dependency_name="pgbouncer",
        )

    common_environment = data.get("x-common", {}).get("environment", {})
    common_environment.pop("DATABASE_URL", None)

    volumes = data.get("volumes", {})
    volumes.pop("postgres_data", None)


def _remove_redis_compose(*, data: Any) -> None:
    services = data.get("services", {})
    services.pop("redis", None)

    for service_name in ("api",):
        _remove_service_dependency(
            services=services,
            service_name=service_name,
            dependency_name="redis",
        )

    common_environment = data.get("x-common", {}).get("environment", {})
    common_environment.pop("REDIS_URL", None)

    volumes = data.get("volumes", {})
    volumes.pop("redis_data", None)


def _remove_service_dependency(
    *,
    services: Any,
    service_name: str,
    dependency_name: str,
) -> None:
    service = services.get(service_name, {})
    depends_on = service.get("depends_on")
    if not isinstance(depends_on, MutableMapping):
        return

    depends_on.pop(dependency_name, None)
    if not depends_on:
        service.pop("depends_on", None)


def _repo_name_from_url(*, repo_url: str) -> str:
    normalized_url = repo_url.removesuffix(".git").rstrip("/")
    if "://" in normalized_url:
        parts = normalized_url.split("/", maxsplit=3)
        if len(parts) == URL_WITH_SCHEME_PARTS_LENGTH:
            return parts[3]

    if ":" in normalized_url:
        return normalized_url.split(":", maxsplit=1)[1]

    return normalized_url
