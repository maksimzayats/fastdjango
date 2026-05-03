from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import questionary
from management.setup_wizard import prompts
from management.setup_wizard.models import AuthenticationMode, DatabaseMode, RedisMode, StorageMode
from management.setup_wizard.prompts import (
    _ask_authentication_mode,
    _ask_database_answers,
    _ask_docs_site_url,
    _ask_git_answers,
    _ask_redis_answers,
    _ask_repo_url,
    _ask_storage_answers,
    _default_reinitialize_git_repository,
    _suggest_package_name,
    _validate_distribution_name,
    _validate_optional_http_url,
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


def test_optional_http_url_validation_rejects_git_urls() -> None:
    assert _validate_optional_http_url("") is True
    assert _validate_optional_http_url("https://docs.example.com/reference") is True
    assert _validate_optional_http_url("git@github.com:owner/repo.git") == (
        "Use a URL like https://example.com."
    )


def test_repository_url_prompt_requires_browser_safe_http_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_validator: Callable[[str], bool | str] | None = None

    def fake_optional_text(
        message: str,
        *,
        validate: Callable[[str], bool | str] | None = None,
    ) -> str:
        nonlocal captured_validator
        assert message.startswith("Repository URL")
        captured_validator = validate
        return "https://github.com/acme/acme-api"

    monkeypatch.setattr(prompts, "_optional_text", fake_optional_text)

    assert _ask_repo_url() == "https://github.com/acme/acme-api"
    assert captured_validator is not None
    assert captured_validator("git@github.com:acme/acme-api.git") == (
        "Use a URL like https://example.com."
    )


def test_remote_s3_bucket_defaults_trim_blank_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter(
        (
            "https://s3.example.com",
            "https://cdn.example.com",
            "us-east-1",
            "access-key",
            "secret-key",
            "   ",
            "\t",
        ),
    )

    monkeypatch.setattr(prompts, "_ask_text", lambda *_, **__: next(values))

    answers = _ask_storage_answers(storage_mode=StorageMode.REMOTE_S3)

    assert answers.s3_public_bucket_name == "public"
    assert answers.s3_protected_bucket_name == "protected"


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


def test_authentication_mode_prompt_offers_static_api_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_choices: list[Any] = []

    class FakePrompt:
        def ask(self) -> AuthenticationMode:
            return AuthenticationMode.STATIC_API_KEYS

    def fake_select(
        message: str,
        *,
        choices: list[Any],
        default: AuthenticationMode,
    ) -> FakePrompt:
        assert message == "Authentication / authorization"
        assert default == AuthenticationMode.JWT_REFRESH_SESSION
        captured_choices.extend(choices)
        return FakePrompt()

    monkeypatch.setattr(questionary, "select", fake_select)

    assert _ask_authentication_mode() == AuthenticationMode.STATIC_API_KEYS
    assert [choice.value for choice in captured_choices] == [
        AuthenticationMode.JWT_REFRESH_SESSION,
        AuthenticationMode.STATIC_API_KEYS,
        AuthenticationMode.CUSTOM,
    ]


def test_git_prompts_default_to_reinitialize_and_initial_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter((True, True))
    calls: list[tuple[str, bool]] = []

    monkeypatch.setattr(prompts, "_ask_repo_url", lambda: "https://github.com/acme/acme-api")

    def fake_ask_confirm(message: str, *, default: bool) -> bool:
        calls.append((message, default))
        return next(values)

    monkeypatch.setattr(prompts, "_ask_confirm", fake_ask_confirm)

    answers = _ask_git_answers()

    assert answers.repo_url == "https://github.com/acme/acme-api"
    assert answers.reinitialize_git_repository is True
    assert answers.create_initial_commit is True
    assert calls == [
        ("Reinitialize Git repository to remove cloned-template history and old origin?", True),
        ("Create generated project setup commit?", True),
    ]


def test_git_prompts_can_preserve_git_and_create_initial_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter((False, True))
    calls: list[tuple[str, bool]] = []

    monkeypatch.setattr(prompts, "_ask_repo_url", lambda: None)

    def fake_ask_confirm(message: str, *, default: bool) -> bool:
        calls.append((message, default))
        return next(values)

    monkeypatch.setattr(prompts, "_ask_confirm", fake_ask_confirm)

    answers = _ask_git_answers()

    assert answers.repo_url is None
    assert answers.reinitialize_git_repository is False
    assert answers.create_initial_commit is True
    assert calls == [
        ("Reinitialize Git repository to remove cloned-template history and old origin?", True),
        ("Create generated project setup commit?", True),
    ]


def test_user_owned_http_origin_skips_repo_url_and_reinitialize_prompts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        prompts,
        "_current_origin_url",
        _fake_origin_url("https://github.com/acme/acme-api.git"),
    )

    def fail_ask_repo_url() -> str | None:
        pytest.fail("Repository URL should be inferred from a user-owned GitHub origin.")

    def fake_ask_confirm(message: str, *, default: bool) -> bool:
        calls.append((message, default))
        return True

    monkeypatch.setattr(prompts, "_ask_repo_url", fail_ask_repo_url)
    monkeypatch.setattr(prompts, "_ask_confirm", fake_ask_confirm)

    answers = _ask_git_answers(repo_root=tmp_path)

    assert answers.repo_url == "https://github.com/acme/acme-api"
    assert answers.reinitialize_git_repository is False
    assert answers.create_initial_commit is True
    assert calls == [("Create generated project setup commit?", True)]
    assert _default_reinitialize_git_repository(repo_root=tmp_path) is False


@pytest.mark.parametrize(
    "origin_url",
    [
        "git@github.com:acme/acme-api.git",
        "ssh://git@github.com/acme/acme-api.git",
    ],
)
def test_user_owned_ssh_origin_is_inferred_as_https_repo_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    origin_url: str,
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(prompts, "_current_origin_url", _fake_origin_url(origin_url))
    monkeypatch.setattr(
        prompts,
        "_ask_repo_url",
        lambda: pytest.fail("Repository URL should be inferred from GitHub SSH origin."),
    )
    monkeypatch.setattr(prompts, "_ask_confirm", lambda *_args, **_kwargs: False)

    answers = _ask_git_answers(repo_root=tmp_path)

    assert answers.repo_url == "https://github.com/acme/acme-api"
    assert answers.reinitialize_git_repository is False
    assert answers.create_initial_commit is False


def test_git_reinitialize_default_is_true_for_template_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        prompts,
        "_current_origin_url",
        _fake_origin_url("git@github.com:MaksimZayats/fastdjango.git"),
    )

    def fake_ask_confirm(message: str, *, default: bool) -> bool:
        calls.append((message, default))
        return True

    monkeypatch.setattr(prompts, "_ask_repo_url", lambda: "https://github.com/acme/acme-api")
    monkeypatch.setattr(prompts, "_ask_confirm", fake_ask_confirm)

    answers = _ask_git_answers(repo_root=tmp_path)

    assert answers.repo_url == "https://github.com/acme/acme-api"
    assert answers.reinitialize_git_repository is True
    assert answers.create_initial_commit is True
    assert calls == [
        ("Reinitialize Git repository to remove cloned-template history and old origin?", True),
        ("Create generated project setup commit?", True),
    ]
    assert _default_reinitialize_git_repository(repo_root=tmp_path) is True


def test_template_origin_detection_normalizes_git_suffix_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        prompts,
        "_current_origin_url",
        _fake_origin_url("https://github.com/MaksimZayats/fastdjango.GIT/"),
    )
    monkeypatch.setattr(prompts, "_ask_repo_url", lambda: "https://github.com/acme/acme-api")
    monkeypatch.setattr(prompts, "_ask_confirm", lambda *_args, **kwargs: kwargs["default"])

    answers = _ask_git_answers(repo_root=tmp_path)

    assert answers.reinitialize_git_repository is True
    assert _default_reinitialize_git_repository(repo_root=tmp_path) is True


def test_existing_repo_with_no_origin_keeps_explicit_prompt_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(prompts, "_current_origin_url", _fake_origin_url(None))

    def fake_ask_confirm(message: str, *, default: bool) -> bool:
        calls.append((message, default))
        return default

    monkeypatch.setattr(prompts, "_ask_repo_url", lambda: "https://github.com/acme/acme-api")
    monkeypatch.setattr(prompts, "_ask_confirm", fake_ask_confirm)

    answers = _ask_git_answers(repo_root=tmp_path)

    assert answers.repo_url == "https://github.com/acme/acme-api"
    assert answers.reinitialize_git_repository is False
    assert answers.create_initial_commit is True
    assert calls == [
        ("Reinitialize Git repository to remove cloned-template history and old origin?", False),
        ("Create generated project setup commit?", True),
    ]
    assert _default_reinitialize_git_repository(repo_root=tmp_path) is False


@pytest.mark.parametrize(
    "origin_url",
    [
        "file:///tmp/acme-api.git",
        "../acme-api.git",
    ],
)
def test_unsupported_local_origins_do_not_get_forced_into_docs_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    origin_url: str,
) -> None:
    (tmp_path / ".git").mkdir()
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(prompts, "_current_origin_url", _fake_origin_url(origin_url))

    def fake_ask_confirm(message: str, *, default: bool) -> bool:
        calls.append((message, default))
        return default

    monkeypatch.setattr(prompts, "_ask_repo_url", lambda: None)
    monkeypatch.setattr(prompts, "_ask_confirm", fake_ask_confirm)

    answers = _ask_git_answers(repo_root=tmp_path)

    assert answers.repo_url is None
    assert answers.reinitialize_git_repository is False
    assert answers.create_initial_commit is True
    assert calls == [
        ("Reinitialize Git repository to remove cloned-template history and old origin?", False),
        ("Create generated project setup commit?", True),
    ]


def test_git_reinitialize_default_is_true_without_existing_git_repo(tmp_path: Path) -> None:
    assert _default_reinitialize_git_repository(repo_root=tmp_path) is True


def _fake_origin_url(value: str | None) -> Callable[..., str | None]:
    def fake_current_origin_url(*, repo_root: Path) -> str | None:
        assert repo_root.name
        return value

    return fake_current_origin_url
