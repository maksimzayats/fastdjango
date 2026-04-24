from typing import Literal

from fastdjango.foundation.delivery.celery.schemas import BaseCelerySchema


class PingResultSchema(BaseCelerySchema):
    result: Literal["pong"]
