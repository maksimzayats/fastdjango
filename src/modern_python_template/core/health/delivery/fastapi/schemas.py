from typing import Literal

from modern_python_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class HealthCheckResponseSchema(BaseFastAPISchema):
    status: Literal["ok"]
