from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from management.setup_wizard.file_operations import FilePlan
from management.setup_wizard.models import (
    DatabaseMode,
    FileOperation,
    RedisMode,
    SetupAnswers,
    StorageMode,
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
            title="FastDjango Setup",
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
    _render_plan_summary(console=console, plan=plan)

    if args.dry_run:
        console.print("[green]Dry run complete. No files were changed.[/green]")
        return 0

    try:
        if not confirm_plan():
            console.print("[yellow]Setup cancelled.[/yellow]")
            return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        return 130

    plan.apply()
    console.print("[green]Setup complete.[/green]")
    _render_next_steps(console=console, answers=answers)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FastDjango one-time setup wizard.")
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


def _render_plan_summary(*, console: Console, plan: FilePlan) -> None:
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

    console.print(table)


def _operation_target(*, plan: FilePlan, operation: FileOperation) -> str:
    if operation.kind == "rename" and operation.target_path is not None:
        return (
            f"{plan.relative_path(operation.path)} -> {plan.relative_path(operation.target_path)}"
        )

    if operation.kind == "command" and operation.command is not None:
        return " ".join(operation.command)

    return plan.relative_path(operation.path)


def _render_next_steps(*, console: Console, answers: SetupAnswers) -> None:
    table = Table(title="Next steps")
    table.add_column("Step")
    table.add_column("Command")

    table.add_row("Install dependencies", "uv sync --locked --all-groups")

    docker_services = _docker_services(answers=answers)
    if docker_services:
        table.add_row("Start local services", f"docker compose up -d {' '.join(docker_services)}")

    if answers.storage_mode == StorageMode.MINIO:
        table.add_row("Create MinIO buckets", "docker compose up minio-create-buckets")

    table.add_row("Apply migrations", "make migrate")
    table.add_row("Collect static files", "make collectstatic")
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
    if answers.storage_mode == StorageMode.MINIO:
        services.append("minio")
    return services
