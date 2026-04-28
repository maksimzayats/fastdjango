from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from management.dependency_updater import (
    ProgressReporter,
    UpdateOptions,
    sync_pyproject_dependency_versions,
    update_container_image_versions,
    update_dependencies,
    update_github_action_versions,
)

from management import dependency_updater


def test_update_dependencies_prints_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def sync_stub(**_: object) -> tuple[dependency_updater.DependencyUpdate, ...]:
        return ()

    monkeypatch.setattr(
        dependency_updater,
        "sync_pyproject_dependency_versions",
        sync_stub,
    )

    update_dependencies(
        repo_root=tmp_path,
        options=UpdateOptions(
            dry_run=True,
            upgrade_lock=False,
            update_pyproject=True,
            update_actions=False,
            update_containers=False,
        ),
        progress=ProgressReporter(enabled=True),
    )

    assert capsys.readouterr().out == (
        "Syncing pyproject.toml dependency bounds...\n"
        "Syncing pyproject.toml dependency bounds: done\n"
    )


def test_sync_pyproject_dependency_versions_uses_locked_direct_versions(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            dependencies = [
                "django>6",
                "django-storages[s3]>=1.14.0",
            ]

            [dependency-groups]
            dev = [
                "pytest>=9.0.0",
            ]

            [build-system]
            requires = ["uv_build>=0.11.0,<0.12.0"]
            """,
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text(
        textwrap.dedent(
            """
            version = 1

            [[package]]
            name = "django"
            version = "6.0.4"

            [[package]]
            name = "django-storages"
            version = "1.14.6"

            [[package]]
            name = "pytest"
            version = "9.0.3"
            """,
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    updates = sync_pyproject_dependency_versions(
        repo_root=tmp_path,
        latest_version_resolver=lambda package_name: (
            "0.11.8" if package_name == "uv_build" else None
        ),
    )

    assert {update.new_requirement for update in updates} == {
        "django>=6.0.4",
        "django-storages[s3]>=1.14.6",
        "pytest>=9.0.3",
        "uv_build>=0.11.8,<0.12.0",
    }
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == textwrap.dedent(
        """
        [project]
        dependencies = [
            "django>=6.0.4",
            "django-storages[s3]>=1.14.6",
        ]

        [dependency-groups]
        dev = [
            "pytest>=9.0.3",
        ]

        [build-system]
        requires = ["uv_build>=0.11.8,<0.12.0"]
        """,
    ).lstrip()


def test_sync_pyproject_dependency_versions_preserves_upper_bounds(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            dependencies = []

            [build-system]
            requires = ["uv_build>=0.11.0,<0.12.0"]
            """,
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    updates = sync_pyproject_dependency_versions(
        repo_root=tmp_path,
        latest_version_resolver=lambda package_name: (
            "0.12.0" if package_name == "uv_build" else None
        ),
    )

    assert updates == ()
    assert 'requires = ["uv_build>=0.11.0,<0.12.0"]' in (tmp_path / "pyproject.toml").read_text(
        encoding="utf-8",
    )


def test_update_github_action_versions_preserves_major_refs(tmp_path: Path) -> None:
    workflows_path = tmp_path / ".github" / "workflows"
    workflows_path.mkdir(parents=True)
    workflow_path = workflows_path / "ci.yaml"
    workflow_path.write_text(
        textwrap.dedent(
            """
            name: CI

            jobs:
              check:
                steps:
                  - uses: actions/checkout@v6
                  - uses: astral-sh/setup-uv@v7
                  - uses: docker/setup-compose-action@v1
            """,
        ).lstrip(),
        encoding="utf-8",
    )

    updates = update_github_action_versions(
        repo_root=tmp_path,
        latest_tag_resolver=lambda repository: {
            "actions/checkout": "v6.0.2",
            "astral-sh/setup-uv": "v8.1.0",
            "docker/setup-compose-action": "v2.1.0",
        }[repository],
    )

    assert [(update.repository, update.old_ref, update.new_ref) for update in updates] == [
        ("astral-sh/setup-uv", "v7", "v8"),
        ("docker/setup-compose-action", "v1", "v2"),
    ]
    assert "actions/checkout@v6" in workflow_path.read_text(encoding="utf-8")
    assert "astral-sh/setup-uv@v8" in workflow_path.read_text(encoding="utf-8")
    assert "docker/setup-compose-action@v2" in workflow_path.read_text(encoding="utf-8")


def test_update_container_image_versions_updates_docker_files_and_docs(tmp_path: Path) -> None:
    docker_path = tmp_path / "docker"
    docker_path.mkdir()
    dockerfile_path = docker_path / "Dockerfile"
    compose_path = docker_path / "docker-compose.yaml"
    docs_path = tmp_path / "docs" / "en" / "reference"
    docs_path.mkdir(parents=True)
    docker_docs_path = docs_path / "docker-services.md"

    dockerfile_path.write_text(
        textwrap.dedent(
            """
            FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
            FROM python:3.14-slim-bookworm
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    compose_path.write_text(
        textwrap.dedent(
            """
            services:
              base:
                image: base:local
              postgres:
                image: postgres:18-alpine
              redis:
                image: redis:latest
              pgbouncer:
                image: edoburu/pgbouncer:latest
              minio-create-buckets:
                image: minio/mc
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    docker_docs_path.write_text(
        "Images: postgres:18-alpine, redis:latest, edoburu/pgbouncer, minio/mc.\n",
        encoding="utf-8",
    )

    updates = update_container_image_versions(
        repo_root=tmp_path,
        latest_tag_resolver=lambda repository, current_tag: {
            ("ghcr.io/astral-sh/uv", "python3.14-bookworm-slim"): (
                "0.9.30-python3.14-bookworm-slim"
            ),
            ("python", "3.14-slim-bookworm"): "3.14.4-slim-bookworm",
            ("postgres", "18-alpine"): "18.3-alpine",
            ("redis", "latest"): "8.6.2",
            ("edoburu/pgbouncer", "latest"): "v1.25.1-p0",
            ("minio/mc", None): "RELEASE.2025-08-13T08-35-41Z",
        }[(repository, current_tag)],
    )

    assert {(update.file_path.name, update.old_ref, update.new_ref) for update in updates} >= {
        ("Dockerfile", "python:3.14-slim-bookworm", "python:3.14.4-slim-bookworm"),
        ("docker-compose.yaml", "postgres:18-alpine", "postgres:18.3-alpine"),
        ("docker-services.md", "redis:latest", "redis:8.6.2"),
    }
    assert "base:local" in compose_path.read_text(encoding="utf-8")
    assert "ghcr.io/astral-sh/uv:0.9.30-python3.14-bookworm-slim" in (
        dockerfile_path.read_text(encoding="utf-8")
    )
    assert "postgres:18.3-alpine" in docker_docs_path.read_text(encoding="utf-8")
    assert "edoburu/pgbouncer:v1.25.1-p0" in docker_docs_path.read_text(encoding="utf-8")
    assert "minio/mc:RELEASE.2025-08-13T08-35-41Z" in docker_docs_path.read_text(
        encoding="utf-8",
    )


def test_update_container_image_versions_ignores_arch_only_tags_for_latest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_path = tmp_path / "docker"
    docker_path.mkdir()
    compose_path = docker_path / "docker-compose.yaml"
    compose_path.write_text(
        textwrap.dedent(
            """
            services:
              redis:
                image: redis:latest
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dependency_updater,
        "_container_registry_tags",
        lambda *, repository: (
            ("32bit-buster", "8.6.2-trixie", "8.6.2") if repository == "redis" else ()
        ),
    )

    updates = dependency_updater.update_container_image_versions(repo_root=tmp_path)

    assert [(update.old_ref, update.new_ref) for update in updates] == [
        ("redis:latest", "redis:8.6.2"),
    ]
    assert "image: redis:8.6.2" in compose_path.read_text(encoding="utf-8")


def test_update_container_image_versions_uses_library_namespace_for_docker_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_path = tmp_path / "docker"
    docker_path.mkdir()
    compose_path = docker_path / "docker-compose.yaml"
    compose_path.write_text(
        textwrap.dedent(
            """
            services:
              app:
                image: docker.io/python:3.14-slim-bookworm
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    requested_paths: list[str] = []

    def docker_hub_tags_stub(*, repository_path: str) -> tuple[str, ...]:
        requested_paths.append(repository_path)
        return ("3.14.4-slim-bookworm",)

    monkeypatch.setattr(dependency_updater, "_docker_hub_tags", docker_hub_tags_stub)

    updates = dependency_updater.update_container_image_versions(repo_root=tmp_path)

    assert requested_paths == ["library/python"]
    assert [(update.old_ref, update.new_ref) for update in updates] == [
        ("docker.io/python:3.14-slim-bookworm", "docker.io/python:3.14.4-slim-bookworm"),
    ]
