from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from management.setup_wizard.models import SetupAnswers

INITIAL_COMMIT_MESSAGE = "initial commit"
INITIAL_BRANCH_NAME = "main"
PRIMARY_INIT_COMMAND = ("git", "init", f"--initial-branch={INITIAL_BRANCH_NAME}")
FALLBACK_INIT_COMMAND = ("git", "init", "-b", INITIAL_BRANCH_NAME)


@dataclass(frozen=True, kw_only=True)
class GitAction:
    kind: Literal["delete", "command", "preserve", "warning"]
    target: str
    detail: str
    command: tuple[str, ...] | None = None


@dataclass(frozen=True, kw_only=True)
class GitPlan:
    repo_root: Path
    reinitialize_git_repository: bool
    had_git_repository: bool
    repo_url: str | None
    create_initial_commit: bool
    actions: tuple[GitAction, ...]


@dataclass(frozen=True, kw_only=True)
class GitSetupResult:
    reinitialized: bool
    had_git_repository: bool = True
    origin_added: bool = False
    initial_commit_created: bool = False
    initial_commit_failed: bool = False
    initial_commit_stdout: str = ""
    initial_commit_stderr: str = ""


def build_git_plan(*, repo_root: Path, answers: SetupAnswers) -> GitPlan:
    actions: list[GitAction] = []
    has_git_repository = (repo_root / ".git").exists()
    if not answers.reinitialize_git_repository:
        actions.append(
            GitAction(
                kind="preserve" if has_git_repository else "warning",
                target=".git",
                detail=(
                    "Keep existing Git history and origin"
                    if has_git_repository
                    else "No Git repository exists, so no initial commit can be created"
                ),
            ),
        )
        create_initial_commit = answers.create_initial_commit and has_git_repository
        if create_initial_commit:
            actions.extend(_initial_commit_actions())

        return GitPlan(
            repo_root=repo_root,
            reinitialize_git_repository=False,
            had_git_repository=has_git_repository,
            repo_url=answers.repo_url,
            create_initial_commit=create_initial_commit,
            actions=tuple(actions),
        )

    if has_git_repository:
        actions.append(
            GitAction(
                kind="delete",
                target=".git",
                detail="Remove template Git history and remotes",
            ),
        )

    actions.append(
        GitAction(
            kind="command",
            target="git init --initial-branch=main",
            detail="Initialize a fresh Git repository",
            command=PRIMARY_INIT_COMMAND,
        ),
    )

    if answers.repo_url is not None:
        actions.append(
            GitAction(
                kind="command",
                target=f"git remote add origin {answers.repo_url}",
                detail="Set Git origin to the entered repository URL",
                command=("git", "remote", "add", "origin", answers.repo_url),
            ),
        )

    if answers.create_initial_commit:
        actions.extend(_initial_commit_actions())

    return GitPlan(
        repo_root=repo_root,
        reinitialize_git_repository=True,
        had_git_repository=has_git_repository,
        repo_url=answers.repo_url,
        create_initial_commit=answers.create_initial_commit,
        actions=tuple(actions),
    )


def apply_git_plan(*, plan: GitPlan) -> GitSetupResult:
    if not plan.reinitialize_git_repository:
        return _apply_initial_commit_plan(plan=plan, reinitialized=False, origin_added=False)

    _git_executable()
    git_dir = plan.repo_root / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    _run_git_init_command(plan=plan)

    origin_added = False
    if plan.repo_url is not None:
        _run_git_command(command=("git", "remote", "add", "origin", plan.repo_url), plan=plan)
        origin_added = True

    if not plan.create_initial_commit:
        return GitSetupResult(
            reinitialized=True,
            had_git_repository=plan.had_git_repository,
            origin_added=origin_added,
        )

    return _apply_initial_commit_plan(
        plan=plan,
        reinitialized=True,
        origin_added=origin_added,
    )


def _initial_commit_actions() -> tuple[GitAction, GitAction]:
    return (
        GitAction(
            kind="command",
            target="git add --all",
            detail="Stage generated project files",
            command=("git", "add", "--all"),
        ),
        GitAction(
            kind="command",
            target='git commit -m "initial commit"',
            detail="Create the initial project commit",
            command=("git", "commit", "-m", INITIAL_COMMIT_MESSAGE),
        ),
    )


def _apply_initial_commit_plan(
    *,
    plan: GitPlan,
    reinitialized: bool,
    origin_added: bool,
) -> GitSetupResult:
    if not plan.create_initial_commit:
        return GitSetupResult(
            reinitialized=reinitialized,
            had_git_repository=plan.had_git_repository,
            origin_added=origin_added,
        )

    _run_git_command(command=("git", "add", "--all"), plan=plan)
    git_path = _git_executable()
    commit_result = subprocess.run(  # noqa: S603
        (git_path, "commit", "-m", INITIAL_COMMIT_MESSAGE),
        cwd=plan.repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    if commit_result.returncode != 0:
        return GitSetupResult(
            reinitialized=reinitialized,
            had_git_repository=plan.had_git_repository,
            origin_added=origin_added,
            initial_commit_failed=True,
            initial_commit_stdout=commit_result.stdout,
            initial_commit_stderr=commit_result.stderr,
        )

    return GitSetupResult(
        reinitialized=reinitialized,
        had_git_repository=plan.had_git_repository,
        origin_added=origin_added,
        initial_commit_created=True,
        initial_commit_stdout=commit_result.stdout,
        initial_commit_stderr=commit_result.stderr,
    )


def _run_git_init_command(*, plan: GitPlan) -> None:
    primary_result = _run_git_command(command=PRIMARY_INIT_COMMAND, plan=plan, check=False)
    if primary_result.returncode == 0:
        return

    if not _is_unsupported_initial_branch_error(result=primary_result):
        primary_result.check_returncode()

    fallback_result = _run_git_command(command=FALLBACK_INIT_COMMAND, plan=plan, check=False)
    if fallback_result.returncode == 0:
        return

    msg = (
        "Git repository initialization failed with both supported commands:\n"
        f"- {' '.join(PRIMARY_INIT_COMMAND)}: "
        f"{_git_error_message(result=primary_result)}\n"
        f"- {' '.join(FALLBACK_INIT_COMMAND)}: "
        f"{_git_error_message(result=fallback_result)}"
    )
    raise RuntimeError(msg)


def _is_unsupported_initial_branch_error(
    *,
    result: subprocess.CompletedProcess[str],
) -> bool:
    output = f"{result.stdout}\n{result.stderr}".casefold()
    return "initial-branch" in output and (
        "unknown option" in output or "unrecognized option" in output or "invalid option" in output
    )


def _git_error_message(*, result: subprocess.CompletedProcess[str]) -> str:
    stderr = result.stderr or ""
    stdout = result.stdout or ""
    output = f"{stderr.strip()} {stdout.strip()}".strip()
    return output or f"exit code {result.returncode}"


def _run_git_command(
    *,
    command: tuple[str, ...],
    plan: GitPlan,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        (_git_executable(), *command[1:]),
        cwd=plan.repo_root,
        capture_output=not check,
        check=check,
        text=True,
    )


def _git_executable() -> str:
    git_path = shutil.which("git")
    if git_path is None:
        msg = "git executable was not found."
        raise FileNotFoundError(msg)

    return git_path
