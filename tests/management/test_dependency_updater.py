from __future__ import annotations

import textwrap
from pathlib import Path

import management.dependency_updater.update_container_image_versions as container_updater
import management.dependency_updater.update_dependencies as dependency_runner
import pytest
from management.dependency_updater.dependency_update import DependencyUpdate
from management.dependency_updater.progress_reporter import ProgressReporter
from management.dependency_updater.sync_pyproject_dependency_versions import (
    sync_pyproject_dependency_versions,
)
from management.dependency_updater.update_container_image_versions import (
    update_container_image_versions,
)
from management.dependency_updater.update_dependencies import update_dependencies
from management.dependency_updater.update_github_action_versions import (
    update_github_action_versions,
)
from management.dependency_updater.update_options import UpdateOptions


def test_update_dependencies_prints_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def sync_stub(**_: object) -> tuple[DependencyUpdate, ...]:
        return ()

    monkeypatch.setattr(
        dependency_runner,
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
                "fastapi>0.138",
                "sqlalchemy[asyncio]>=2.0.40",
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
            name = "fastapi"
            version = "0.138.1"

            [[package]]
            name = "sqlalchemy"
            version = "2.0.45"

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
        "fastapi>=0.138.1",
        "sqlalchemy[asyncio]>=2.0.45",
        "pytest>=9.0.3",
        "uv_build>=0.11.8,<0.12.0",
    }
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == textwrap.dedent(
        """
        [project]
        dependencies = [
            "fastapi>=0.138.1",
            "sqlalchemy[asyncio]>=2.0.45",
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


def test_update_github_action_versions_uses_real_latest_tags_for_new_majors(
    tmp_path: Path,
) -> None:
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
                  - name: Set up Docker Compose
                    uses: docker/setup-compose-action@v1
                    with:
                      version: latest
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
            "docker/compose": "v5.1.3",
        }[repository],
    )

    assert [(update.repository, update.old_ref, update.new_ref) for update in updates] == [
        ("astral-sh/setup-uv", "v7", "v8.1.0"),
        ("docker/setup-compose-action", "v1", "v2.1.0"),
        ("docker/compose", "latest", "v5.1.3"),
    ]
    assert "actions/checkout@v6" in workflow_path.read_text(encoding="utf-8")
    assert "astral-sh/setup-uv@v8.1.0" in workflow_path.read_text(encoding="utf-8")
    assert "docker/setup-compose-action@v2.1.0" in workflow_path.read_text(encoding="utf-8")
    assert "version: v5.1.3" in workflow_path.read_text(encoding="utf-8")


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
              image-tool:
                image: curlimages/curl
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    docker_docs_path.write_text(
        "Images: postgres:18-alpine, redis:latest, edoburu/pgbouncer, curlimages/curl.\n",
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
            ("curlimages/curl", None): "8.16.0",
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
    assert "curlimages/curl:8.16.0" in docker_docs_path.read_text(
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
        container_updater,
        "_container_registry_tags",
        lambda *, repository: (
            ("32bit-buster", "8.6.2-trixie", "8.6.2") if repository == "redis" else ()
        ),
    )

    updates = container_updater.update_container_image_versions(repo_root=tmp_path)

    assert [(update.old_ref, update.new_ref) for update in updates] == [
        ("redis:latest", "redis:8.6.2"),
    ]
    assert "image: redis:8.6.2" in compose_path.read_text(encoding="utf-8")


def test_update_container_image_versions_does_not_downgrade_dotted_versions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_path = tmp_path / "docker"
    docker_path.mkdir()
    dockerfile_path = docker_path / "Dockerfile"
    dockerfile_path.write_text(
        "FROM ghcr.io/astral-sh/uv:0.11.8 AS uv\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        container_updater,
        "_container_registry_tags",
        lambda *, repository: (
            ("0.11.8", "0.10.1", "0.9.28") if repository == "ghcr.io/astral-sh/uv" else ()
        ),
    )

    updates = container_updater.update_container_image_versions(repo_root=tmp_path)

    assert updates == ()
    assert "ghcr.io/astral-sh/uv:0.11.8" in dockerfile_path.read_text(encoding="utf-8")


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

    monkeypatch.setattr(container_updater, "_docker_hub_tags", docker_hub_tags_stub)

    updates = container_updater.update_container_image_versions(repo_root=tmp_path)

    assert requested_paths == ["library/python"]
    assert [(update.old_ref, update.new_ref) for update in updates] == [
        ("docker.io/python:3.14-slim-bookworm", "docker.io/python:3.14.4-slim-bookworm"),
    ]


def test_update_container_image_versions_does_not_rewrite_longer_image_refs(
    tmp_path: Path,
) -> None:
    docker_path = tmp_path / "docker"
    docker_path.mkdir()
    compose_path = docker_path / "docker-compose.yaml"
    docs_path = tmp_path / "docs" / "en" / "reference"
    docs_path.mkdir(parents=True)
    docker_docs_path = docs_path / "docker-services.md"

    compose_path.write_text(
        textwrap.dedent(
            """
            services:
              redis:
                image: redis:latest
              curl-client:
                image: curlimages/curl
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    docker_docs_path.write_text(
        (
            "Use redis:latest. Do not touch redis:latest-alpine or "
            "curlimages/curl-debug. Use curlimages/curl.\n"
        ),
        encoding="utf-8",
    )

    update_container_image_versions(
        repo_root=tmp_path,
        latest_tag_resolver=lambda repository, current_tag: {
            ("redis", "latest"): "8.6.2",
            ("curlimages/curl", None): "8.16.0",
        }[(repository, current_tag)],
    )

    updated_docs = docker_docs_path.read_text(encoding="utf-8")
    assert "redis:8.6.2." in updated_docs
    assert "redis:latest-alpine" in updated_docs
    assert "curlimages/curl-debug" in updated_docs
    assert "curlimages/curl:8.16.0." in updated_docs
