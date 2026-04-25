from typing import Literal

from fastdjango.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class HealthCheckResponseSchema(BaseFastAPISchema):
    status: Literal["ok"]
