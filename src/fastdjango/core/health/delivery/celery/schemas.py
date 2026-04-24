from typing import Literal

from fastdjango.core.shared.delivery.celery.schemas import BaseCelerySchema


class PingResultSchema(BaseCelerySchema):
    result: Literal["pong"]
