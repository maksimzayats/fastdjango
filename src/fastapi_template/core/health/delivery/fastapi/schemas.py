from typing import Literal

from fastapi_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class HealthCheckResponseSchema(BaseFastAPISchema):
    status: Literal["ok"]
