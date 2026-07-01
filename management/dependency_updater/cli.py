import argparse
from collections.abc import Sequence
from pathlib import Path

from management.dependency_updater.output import _write_line
from management.dependency_updater.progress_reporter import ProgressReporter
from management.dependency_updater.update_dependencies import update_dependencies
from management.dependency_updater.update_options import UpdateOptions
from management.dependency_updater.update_summary import UpdateSummary

_STORE_TRUE_ACTION = "store_true"


def main(argv: Sequence[str] | None = None) -> int:
    """Parse dependency-updater arguments and execute the selected updates.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Update uv lock, pyproject dependency lower bounds, "
            "GitHub Action pins, and container image pins."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to update. Defaults to the current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action=_STORE_TRUE_ACTION,
        help="Print planned changes without writing files or running uv lock --upgrade.",
    )
    parser.add_argument(
        "--skip-lock-upgrade",
        action=_STORE_TRUE_ACTION,
        help="Do not run uv lock --upgrade before syncing pyproject.toml.",
    )
    parser.add_argument(
        "--skip-pyproject",
        action=_STORE_TRUE_ACTION,
        help="Do not sync pyproject.toml dependency lower bounds.",
    )
    parser.add_argument(
        "--skip-actions",
        action=_STORE_TRUE_ACTION,
        help="Do not update GitHub Action versions in .github/workflows.",
    )
    parser.add_argument(
        "--skip-containers",
        action=_STORE_TRUE_ACTION,
        help="Do not update Dockerfile or Docker Compose image pins.",
    )
    parser.add_argument(
        "--quiet",
        action=_STORE_TRUE_ACTION,
        help="Hide updater progress messages.",
    )
    args = parser.parse_args(argv)

    summary = update_dependencies(
        repo_root=args.repo_root,
        options=UpdateOptions(
            dry_run=args.dry_run,
            upgrade_lock=not args.skip_lock_upgrade,
            update_pyproject=not args.skip_pyproject,
            update_actions=not args.skip_actions,
            update_containers=not args.skip_containers,
        ),
        progress=ProgressReporter(enabled=not args.quiet),
    )

    _print_summary(summary=summary, dry_run=args.dry_run)
    return 0


def _print_summary(*, summary: UpdateSummary, dry_run: bool) -> None:
    prefix = "Would update" if dry_run else "Updated"
    if not any(
        (
            summary.dependency_updates,
            summary.action_updates,
            summary.container_updates,
        ),
    ):
        _write_line("No dependency updates found.")
        return

    for dependency_update in summary.dependency_updates:
        _write_line(
            f"{prefix} dependency "
            f"{dependency_update.old_requirement} -> {dependency_update.new_requirement}",
        )

    for action_update in summary.action_updates:
        _write_line(
            f"{prefix} action "
            f"{action_update.file_path}: {action_update.repository}@{action_update.old_ref} "
            f"-> {action_update.repository}@{action_update.new_ref}",
        )

    for container_update in summary.container_updates:
        _write_line(
            f"{prefix} image "
            f"{container_update.file_path}: {container_update.old_ref} "
            f"-> {container_update.new_ref}",
        )
