from dataclasses import dataclass

from management.dependency_updater.action_update import ActionUpdate
from management.dependency_updater.container_image_update import ContainerImageUpdate
from management.dependency_updater.dependency_update import DependencyUpdate


@dataclass(frozen=True, kw_only=True)
class UpdateSummary:
    """Describe every update made by one dependency updater run."""

    dependency_updates: tuple[DependencyUpdate, ...]
    action_updates: tuple[ActionUpdate, ...]
    container_updates: tuple[ContainerImageUpdate, ...]
