import subprocess
from collections.abc import Sequence
from pathlib import Path

from management.dependency_updater.action_update import ActionUpdate
from management.dependency_updater.container_image_update import ContainerImageUpdate
from management.dependency_updater.dependency_update import DependencyUpdate
from management.dependency_updater.progress_reporter import ProgressReporter
from management.dependency_updater.sync_pyproject_dependency_versions import (
    sync_pyproject_dependency_versions,
)
from management.dependency_updater.update_container_image_versions import (
    update_container_image_versions,
)
from management.dependency_updater.update_github_action_versions import (
    update_github_action_versions,
)
from management.dependency_updater.update_options import UpdateOptions
from management.dependency_updater.update_summary import UpdateSummary


def update_dependencies(
    *,
    repo_root: Path,
    options: UpdateOptions | None = None,
    progress: ProgressReporter | None = None,
) -> UpdateSummary:
    """Update dependency metadata across the repository.

    Args:
        repo_root: Repository root to update.
        options: Optional update behavior flags.
        progress: Optional progress reporter.

    Returns:
        Summary of updates that were applied or planned.
    """
    update_options = options or UpdateOptions()
    progress_reporter = progress or ProgressReporter(enabled=False)

    if update_options.upgrade_lock and not update_options.dry_run:
        with progress_reporter.step("Updating uv.lock", spinner=False):
            _run_command(["uv", "lock", "--upgrade"], repo_root=repo_root)

    dependency_updates = _update_pyproject_dependencies(
        repo_root=repo_root,
        options=update_options,
        progress=progress_reporter,
    )
    action_updates = _update_github_actions(
        repo_root=repo_root,
        options=update_options,
        progress=progress_reporter,
    )
    container_updates = _update_container_images(
        repo_root=repo_root,
        options=update_options,
        progress=progress_reporter,
    )

    if dependency_updates and not update_options.dry_run:
        with progress_reporter.step("Refreshing uv.lock", spinner=False):
            _run_command(["uv", "lock"], repo_root=repo_root)

    return UpdateSummary(
        dependency_updates=dependency_updates,
        action_updates=action_updates,
        container_updates=container_updates,
    )


def _update_pyproject_dependencies(
    *,
    repo_root: Path,
    options: UpdateOptions,
    progress: ProgressReporter,
) -> tuple[DependencyUpdate, ...]:
    if not options.update_pyproject:
        return ()

    with progress.step("Syncing pyproject.toml dependency bounds"):
        return sync_pyproject_dependency_versions(
            repo_root=repo_root,
            dry_run=options.dry_run,
        )


def _update_github_actions(
    *,
    repo_root: Path,
    options: UpdateOptions,
    progress: ProgressReporter,
) -> tuple[ActionUpdate, ...]:
    if not options.update_actions:
        return ()

    with progress.step("Checking GitHub Action pins"):
        return update_github_action_versions(
            repo_root=repo_root,
            dry_run=options.dry_run,
        )


def _update_container_images(
    *,
    repo_root: Path,
    options: UpdateOptions,
    progress: ProgressReporter,
) -> tuple[ContainerImageUpdate, ...]:
    if not options.update_containers:
        return ()

    with progress.step("Checking Docker and Compose image pins"):
        return update_container_image_versions(
            repo_root=repo_root,
            dry_run=options.dry_run,
        )


def _run_command(command: Sequence[str], *, repo_root: Path) -> None:
    subprocess.run(command, check=True, cwd=repo_root)  # noqa: S603
