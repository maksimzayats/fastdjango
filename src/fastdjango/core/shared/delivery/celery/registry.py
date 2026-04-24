from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from celery import Task

from fastdjango.infrastructure.celery.registry import BaseTasksRegistry

if TYPE_CHECKING:
    from fastdjango.core.health.delivery.celery.tasks import PingResult


class TaskName(StrEnum):
    PING = "ping"


@dataclass(kw_only=True)
class TasksRegistry(BaseTasksRegistry):
    @property
    def ping(self) -> Task[[], PingResult]:
        return self._get_task_by_name(TaskName.PING)
