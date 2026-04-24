from celery import Celery

from fastdjango.core.health.delivery.celery.schemas import PingResultSchema
from fastdjango.core.shared.delivery.celery.registry import TaskName
from fastdjango.infrastructure.delivery.controllers import Controller


class PingTaskController(Controller):
    def register(self, registry: Celery) -> None:
        registry.task(name=TaskName.PING)(self.ping)

    def ping(self) -> PingResultSchema:
        return PingResultSchema(result="pong")
