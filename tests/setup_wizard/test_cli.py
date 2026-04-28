from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from management.setup_wizard import cli
from management.setup_wizard.cli import _checkout_rename, _render_git_result
from management.setup_wizard.file_operations import FilePlan
from management.setup_wizard.git import GitSetupResult
from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers, StorageMode
from rich.console import Console


def test_dry_run_renders_git_actions_without_applying(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git_config_path = tmp_path / ".git" / "config"
    _write(git_config_path, '[remote "origin"]\n\turl = template\n')
    answers = _answers(repo_url="https://github.com/acme/acme-api")

    def fake_is_dirty_git_tree(*, repo_root: Path) -> bool:
        return False

    def fake_detect_current_package_name(*, repo_root: Path) -> str:
        return "fastdjango"

    def fake_prompt_for_answers(*, repo_root: Path) -> SetupAnswers:
        return answers

    def fake_build_setup_plan(
        *,
        repo_root: Path,
        answers: SetupAnswers,
        current_package_name: str | None = None,
    ) -> FilePlan:
        return FilePlan(repo_root=repo_root)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["setup", "--dry-run"])
    monkeypatch.setattr(cli, "_is_dirty_git_tree", fake_is_dirty_git_tree)
    monkeypatch.setattr(cli, "detect_current_package_name", fake_detect_current_package_name)
    monkeypatch.setattr(cli, "prompt_for_answers", fake_prompt_for_answers)
    monkeypatch.setattr(cli, "build_setup_plan", fake_build_setup_plan)

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "git init --initial-branch=main" in output
    assert "git remote add origin" in output
    assert "https://github.com/acme/acme-api" in output
    assert git_config_path.read_text(encoding="utf-8") == ('[remote "origin"]\n\turl = template\n')


def test_dry_run_renders_checkout_directory_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_path = tmp_path / "fastdjango"
    checkout_path.mkdir()
    answers = _answers()

    def fake_is_dirty_git_tree(*, repo_root: Path) -> bool:
        return False

    def fake_detect_current_package_name(*, repo_root: Path) -> str:
        return "fastdjango"

    def fake_prompt_for_answers(*, repo_root: Path) -> SetupAnswers:
        return answers

    def fake_build_setup_plan(
        *,
        repo_root: Path,
        answers: SetupAnswers,
        current_package_name: str | None = None,
    ) -> FilePlan:
        return FilePlan(repo_root=repo_root)

    monkeypatch.chdir(checkout_path)
    monkeypatch.setattr(sys, "argv", ["setup", "--dry-run"])
    monkeypatch.setattr(cli, "_is_dirty_git_tree", fake_is_dirty_git_tree)
    monkeypatch.setattr(cli, "detect_current_package_name", fake_detect_current_package_name)
    monkeypatch.setattr(cli, "prompt_for_answers", fake_prompt_for_answers)
    monkeypatch.setattr(cli, "build_setup_plan", fake_build_setup_plan)

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "fastdjango -> example-api" in output
    assert checkout_path.exists()
    assert not (tmp_path / "example-api").exists()


def test_checkout_rename_uses_distribution_name(tmp_path: Path) -> None:
    repo_root = tmp_path / "fastdjango"
    repo_root.mkdir()

    checkout_rename = _checkout_rename(repo_root=repo_root, answers=_answers())

    assert checkout_rename is not None
    assert checkout_rename.source_path == repo_root
    assert checkout_rename.target_path == tmp_path / "example-api"


def test_checkout_rename_is_skipped_when_directory_already_matches(tmp_path: Path) -> None:
    repo_root = tmp_path / "example-api"
    repo_root.mkdir()

    assert _checkout_rename(repo_root=repo_root, answers=_answers()) is None


def test_declined_git_reinitialization_prints_warning() -> None:
    output = io.StringIO()
    console = Console(file=output, width=200)

    _render_git_result(
        console=console,
        answers=_answers(reinitialize_git_repository=False),
        result=GitSetupResult(reinitialized=False),
    )

    assert "any existing remote may still point at the template" in output.getvalue()


def test_failed_initial_commit_prints_exact_next_step() -> None:
    output = io.StringIO()
    console = Console(file=output, width=200)

    _render_git_result(
        console=console,
        answers=_answers(),
        result=GitSetupResult(
            reinitialized=True,
            initial_commit_failed=True,
            initial_commit_stderr="Author identity unknown",
        ),
    )

    assert 'git commit -m "initial commit"' in output.getvalue()


def _answers(
    *,
    repo_url: str | None = None,
    reinitialize_git_repository: bool = True,
    create_initial_commit: bool = True,
) -> SetupAnswers:
    return SetupAnswers(
        project_name="Example API",
        package_name="example_api",
        distribution_name="example-api",
        docs_site_url=None,
        storage_mode=StorageMode.LOCAL,
        database_mode=DatabaseMode.DOCKER_POSTGRES,
        redis_mode=RedisMode.DOCKER_REDIS,
        keep_docs=True,
        delete_wizard=False,
        overwrite_env=True,
        repo_url=repo_url,
        reinitialize_git_repository=reinitialize_git_repository,
        create_initial_commit=create_initial_commit,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
