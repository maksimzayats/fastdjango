import pytest
from management.setup_wizard import prompts
from management.setup_wizard.models import DatabaseMode, RedisMode, StorageMode
from management.setup_wizard.prompts import (
    _ask_database_answers,
    _ask_docs_site_url,
    _ask_redis_answers,
    _ask_storage_answers,
    _suggest_package_name,
    _validate_distribution_name,
    _validate_optional_url,
    _validate_package_name,
    _validate_project_name,
)


def test_project_name_validation_rejects_empty_and_template_names() -> None:
    assert _validate_project_name("") == "Project name is required."
    assert _validate_project_name("Fast Django") == (
        "Replace the template project name with your own project name."
    )
    assert _validate_project_name("FastDjango") == (
        "Replace the template project name with your own project name."
    )
    assert _validate_project_name("Acme API") is True


def test_package_name_validation_rejects_template_name() -> None:
    assert _validate_package_name("fastdjango") == (
        "Replace the template package name with your own package name."
    )
    assert _validate_package_name("acme_api") is True


def test_distribution_name_validation_rejects_template_name() -> None:
    assert _validate_distribution_name("fastdjango") == (
        "Replace the template distribution name with your own distribution name."
    )
    assert _validate_distribution_name("acme-api") is True


def test_docs_site_url_prompt_is_skipped_when_docs_are_removed() -> None:
    assert _ask_docs_site_url(keep_docs=False) is None


def test_package_name_suggestion_is_derived_from_project_name() -> None:
    assert _suggest_package_name(project_name="Acme API") == "acmeapi"
    assert _suggest_package_name(project_name="  123 Admin Portal!  ") == "app123adminportal"
    assert _suggest_package_name(project_name="My_Service") == "my_service"


def test_optional_url_validation_accepts_web_and_git_urls() -> None:
    assert _validate_optional_url("") is True
    assert _validate_optional_url("https://docs.example.com/reference") is True
    assert _validate_optional_url("git@github.com:owner/repo.git") is True
    assert _validate_optional_url("not a url") == (
        "Use a URL like https://example.com or git@github.com:owner/repo.git."
    )


def test_local_database_port_is_asked_with_database_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []

    def fake_ask_int(message: str, *, default: int) -> int:
        calls.append((message, default))
        return 15432

    monkeypatch.setattr(prompts, "_ask_int", fake_ask_int)

    answers = _ask_database_answers(database_mode=DatabaseMode.DOCKER_POSTGRES)

    assert answers.postgres_port == 15432
    assert calls == [("PostgreSQL host port", 5432)]


def test_local_redis_port_is_asked_with_redis_details(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_ask_int(message: str, *, default: int) -> int:
        calls.append((message, default))
        return 16379

    monkeypatch.setattr(prompts, "_ask_int", fake_ask_int)

    answers = _ask_redis_answers(redis_mode=RedisMode.DOCKER_REDIS)

    assert answers.redis_port == 16379
    assert calls == [("Redis host port", 6379)]


def test_minio_ports_are_asked_with_storage_details(monkeypatch: pytest.MonkeyPatch) -> None:
    ports = iter((19000, 19001))
    calls: list[tuple[str, int]] = []

    def fake_ask_int(message: str, *, default: int) -> int:
        calls.append((message, default))
        return next(ports)

    monkeypatch.setattr(prompts, "_ask_int", fake_ask_int)

    answers = _ask_storage_answers(storage_mode=StorageMode.MINIO)

    assert answers.minio_api_port == 19000
    assert answers.minio_console_port == 19001
    assert calls == [
        ("MinIO API host port", 9000),
        ("MinIO console host port", 9001),
    ]
