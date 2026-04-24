from typing import Literal

from fastdjango.core.shared.delivery.fastapi.schemas import Schema


class HealthCheckResponseSchema(Schema):
    status: Literal["ok"]
