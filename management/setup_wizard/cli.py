from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from management.setup_wizard.file_operations import FilePlan
from management.setup_wizard.git import (
    GitAction,
    GitPlan,
    GitSetupResult,
    apply_git_plan,
    build_git_plan,
)
from management.setup_wizard.models import (
    DatabaseMode,
    FileOperation,
    RedisMode,
    SetupAnswers,
)
from management.setup_wizard.planner import build_setup_plan, detect_current_package_name
from management.setup_wizard.prompts import confirm_plan, prompt_for_answers


def main() -> int:
    args = _parse_args()
    repo_root = Path.cwd()
    console = Console()

    if _is_dirty_git_tree(repo_root=repo_root) and not args.force:
        console.print(
            "[red]Refusing to run setup with a dirty git tree.[/red] "
            "Commit, stash, or rerun with --force.",
        )
        return 1

    current_package_name = detect_current_package_name(repo_root=repo_root)
    console.print(
        Panel.fit(
            f"Current package: [bold]{current_package_name}[/bold]\n"
            "This wizard will rewrite repository files for your new project.",
            title="fastapi_template setup",
        ),
    )

    try:
        answers = prompt_for_answers(repo_root=repo_root)
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        return 130

    plan = build_setup_plan(
        repo_root=repo_root,
        answers=answers,
        current_package_name=current_package_name,
    )
    git_plan = build_git_plan(repo_root=repo_root, answers=answers)
    checkout_rename = _checkout_rename(repo_root=repo_root, answers=answers)
    _render_plan_summary(
        console=console,
        plan=plan,
        git_plan=git_plan,
        checkout_rename=checkout_rename,
    )

    if args.dry_run:
        console.print("[green]Dry run complete. No files were changed.[/green]")
        return 0

    if checkout_rename is not None and checkout_rename.target_path.exists():
        console.print(
            f"[red]Cannot rename checkout directory because "
            f"{checkout_rename.target_path.as_posix()} already exists.[/red]",
        )
        return 1

    confirmation_exit_code = _confirmation_exit_code(console=console)
    if confirmation_exit_code is not None:
        return confirmation_exit_code

    plan.apply()
    git_result = apply_git_plan(plan=git_plan)
    if checkout_rename is not None:
        checkout_rename.source_path.rename(checkout_rename.target_path)
    console.print("[green]Setup complete.[/green]")
    _render_git_result(console=console, answers=answers, result=git_result)
    _render_next_steps(console=console, answers=answers, checkout_rename=checkout_rename)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fastapi_template one-time setup wizard.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing.",
    )
    parser.add_argument("--force", action="store_true", help="Allow setup with a dirty git tree.")
    return parser.parse_args()


def _is_dirty_git_tree(*, repo_root: Path) -> bool:
    if not (repo_root / ".git").exists():
        return False

    git_path = shutil.which("git")
    if git_path is None:
        return False

    result = subprocess.run(  # noqa: S603
        [git_path, "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _confirmation_exit_code(*, console: Console) -> int | None:
    try:
        if confirm_plan():
            return None
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        return 130

    console.print("[yellow]Setup cancelled.[/yellow]")
    return 1


def _render_plan_summary(
    *,
    console: Console,
    plan: FilePlan,
    git_plan: GitPlan,
    checkout_rename: CheckoutRename | None,
) -> None:
    table = Table(title="Planned changes")
    table.add_column("Action")
    table.add_column("Target")
    table.add_column("Details")

    for operation in plan.operations:
        table.add_row(
            operation.kind,
            _operation_target(plan=plan, operation=operation),
            operation.detail,
        )

    for action in git_plan.actions:
        table.add_row(
            action.kind,
            _git_action_target(action=action),
            action.detail,
        )

    if checkout_rename is not None:
        table.add_row(
            "rename",
            f"{checkout_rename.source_path.name} -> {checkout_rename.target_path.name}",
            "Rename checkout directory",
        )

    console.print(table)


def _operation_target(*, plan: FilePlan, operation: FileOperation) -> str:
    if operation.kind == "rename" and operation.target_path is not None:
        return (
            f"{plan.relative_path(operation.path)} -> {plan.relative_path(operation.target_path)}"
        )

    if operation.kind == "command" and operation.command is not None:
        return " ".join(operation.command)

    return plan.relative_path(operation.path)


def _git_action_target(*, action: GitAction) -> str:
    return action.target


def _render_git_result(
    *,
    console: Console,
    answers: SetupAnswers,
    result: GitSetupResult,
) -> None:
    if not answers.reinitialize_git_repository:
        if not result.had_git_repository:
            console.print(
                "[yellow]No Git repository was found; initial commit creation was skipped.[/yellow]",
            )
            return

        console.print(
            "[yellow]Git repository was preserved; existing origin was not changed.[/yellow]",
        )
        console.print(
            "[yellow]If this checkout was cloned from the original template, verify `git remote -v` before pushing.[/yellow]",
        )
        if not result.initial_commit_failed:
            return

    elif not result.initial_commit_failed:
        return

    if _is_missing_git_identity(result=result):
        console.print(
            "[yellow]Initial commit could not be created because Git identity is not configured.[/yellow]",
        )
    else:
        console.print("[yellow]Initial commit failed. Generated files are staged.[/yellow]")

    console.print('Next step: [bold]git commit -m "initial commit"[/bold]')


def _is_missing_git_identity(*, result: GitSetupResult) -> bool:
    output = f"{result.initial_commit_stdout}\n{result.initial_commit_stderr}"
    return "Author identity unknown" in output or "unable to auto-detect email address" in output


def _checkout_rename(*, repo_root: Path, answers: SetupAnswers) -> CheckoutRename | None:
    target_path = repo_root.parent / answers.distribution_name
    if repo_root == target_path:
        return None

    return CheckoutRename(source_path=repo_root, target_path=target_path)


def _render_next_steps(
    *,
    console: Console,
    answers: SetupAnswers,
    checkout_rename: CheckoutRename | None = None,
) -> None:
    table = Table(title="Next steps")
    table.add_column("Step")
    table.add_column("Command")

    if checkout_rename is not None:
        table.add_row("Refresh shell directory", f"cd ../{checkout_rename.target_path.name}")

    table.add_row("Install dependencies", "uv sync --locked --all-groups")

    docker_services = _docker_services(answers=answers)
    if docker_services:
        table.add_row("Start local services", f"docker compose up -d {' '.join(docker_services)}")

    table.add_row("Apply migrations", "make migrate")
    table.add_row("Run the app", "make dev")

    if answers.keep_docs:
        table.add_row("Serve docs", "make docs")

    console.print(table)


def _docker_services(*, answers: SetupAnswers) -> list[str]:
    services: list[str] = []
    if answers.database_mode == DatabaseMode.DOCKER_POSTGRES:
        services.append("postgres")
    if answers.redis_mode == RedisMode.DOCKER_REDIS:
        services.append("redis")
    return services


@dataclass(frozen=True, kw_only=True)
class CheckoutRename:
    source_path: Path
    target_path: Path
