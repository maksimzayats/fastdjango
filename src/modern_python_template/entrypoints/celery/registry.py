from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from modern_python_template.core.health.delivery.celery.tasks import PING_TASK_NAME
from modern_python_template.infrastructure.celery.registry import BaseTasksRegistry, CeleryTask

if TYPE_CHECKING:
    from modern_python_template.core.health.delivery.celery.schemas import PingResultSchema


class TaskName(StrEnum):
    PING = PING_TASK_NAME


@dataclass(kw_only=True)
class TasksRegistry(BaseTasksRegistry):
    @property
    def ping(self) -> CeleryTask[[], PingResultSchema]:
        return self._get_task_by_name(TaskName.PING)
