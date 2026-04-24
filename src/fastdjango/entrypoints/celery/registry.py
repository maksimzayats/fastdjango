from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from celery import Task

from fastdjango.core.health.delivery.celery.tasks import PING_TASK_NAME
from fastdjango.infrastructure.celery.registry import BaseTasksRegistry

if TYPE_CHECKING:
    from fastdjango.core.health.delivery.celery.schemas import PingResultSchema


class TaskName(StrEnum):
    PING = PING_TASK_NAME


@dataclass(kw_only=True)
class TasksRegistry(BaseTasksRegistry):
    @property
    def ping(self) -> Task[[], PingResultSchema]:
        return self._get_task_by_name(TaskName.PING)
