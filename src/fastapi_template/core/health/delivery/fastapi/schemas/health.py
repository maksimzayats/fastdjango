from typing import Literal

from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class HealthCheckResponseSchema(BaseFastAPISchema):
    """HTTP and websocket payload returned by successful health checks."""

    status: Literal["ok"]
