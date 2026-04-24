from typing import Literal

from fastdjango.core.shared.delivery.fastapi.schemas import BaseFastAPISchema


class HealthCheckResponseSchema(BaseFastAPISchema):
    status: Literal["ok"]
