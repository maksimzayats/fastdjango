from typing import Literal

from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class HealthCheckResponseSchema(BaseFastAPISchema):
    """Define HealthCheckResponseSchema."""

    status: Literal["ok"]
