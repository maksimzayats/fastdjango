from dataclasses import dataclass

from celery import Celery

from fastdjango.core.health.delivery.celery.schemas import PingResultSchema
from fastdjango.infrastructure.celery.controllers import BaseCeleryTaskController

PING_TASK_NAME = "ping"


@dataclass(kw_only=True)
class PingTaskController(BaseCeleryTaskController):
    def register(self, registry: Celery) -> None:
        self._register_task(registry, name=PING_TASK_NAME, handler=self.ping)

    async def ping(self) -> PingResultSchema:
        return PingResultSchema(result="pong")
