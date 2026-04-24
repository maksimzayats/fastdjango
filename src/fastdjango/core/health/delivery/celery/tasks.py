from celery import Celery

from fastdjango.core.health.delivery.celery.schemas import PingResultSchema
from fastdjango.infrastructure.delivery.controllers import Controller

PING_TASK_NAME = "ping"


class PingTaskController(Controller):
    def register(self, registry: Celery) -> None:
        registry.task(name=PING_TASK_NAME)(self.ping)

    def ping(self) -> PingResultSchema:
        return PingResultSchema(result="pong")
