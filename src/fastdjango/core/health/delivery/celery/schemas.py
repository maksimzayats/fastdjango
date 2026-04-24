from typing import Literal

from fastdjango.core.shared.delivery.celery.schemas import CelerySchema


class PingResultSchema(CelerySchema):
    result: Literal["pong"]
