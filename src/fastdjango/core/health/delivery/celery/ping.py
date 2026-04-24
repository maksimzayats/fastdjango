from typing import Literal, TypedDict

from celery import Celery

from fastdjango.core.shared.delivery.celery.registry import TaskName
from fastdjango.infrastructure.delivery.controllers import Controller


class PingResult(TypedDict):
    result: Literal["pong"]


class PingTaskController(Controller):
    def register(self, registry: Celery) -> None:
        registry.task(name=TaskName.PING)(self.ping)

    def ping(self) -> PingResult:
        return PingResult(result="pong")
