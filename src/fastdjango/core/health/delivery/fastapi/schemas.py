from typing import Literal

from fastdjango.core.shared.delivery.fastapi.schemas import FastAPISchema


class HealthCheckResponseSchema(FastAPISchema):
    status: Literal["ok"]
