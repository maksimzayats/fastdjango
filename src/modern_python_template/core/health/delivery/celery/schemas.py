from typing import Literal

from modern_python_template.foundation.delivery.celery.schemas import BaseCelerySchema


class PingResultSchema(BaseCelerySchema):
    result: Literal["pong"]
