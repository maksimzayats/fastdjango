from celery import Celery

from fastdjango.core.health.delivery.celery.schemas import PingResultSchema
from fastdjango.foundation.delivery.controllers import BaseController

PING_TASK_NAME = "ping"


class PingTaskController(BaseController):
    def register(self, registry: Celery) -> None:
        registry.task(name=PING_TASK_NAME)(self.ping)

    def ping(self) -> PingResultSchema:
        return PingResultSchema(result="pong")
