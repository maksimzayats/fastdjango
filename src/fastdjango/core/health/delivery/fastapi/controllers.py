import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fastdjango.core.health.exceptions import HealthCheckError
from fastdjango.core.health.use_cases import SystemHealthUseCase
from fastdjango.infrastructure.delivery.controllers import Controller

logger = logging.getLogger(__name__)


class HealthCheckResponseSchema(BaseModel):
    status: Literal["ok"]


@dataclass(kw_only=True)
class HealthController(Controller):
    _system_health_use_case: SystemHealthUseCase

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/health",
            endpoint=self.health_check,
            methods=["GET"],
        )

    def health_check(self) -> HealthCheckResponseSchema:
        try:
            self._system_health_use_case.check()
        except HealthCheckError as e:
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Service is unavailable",
            ) from e

        return HealthCheckResponseSchema(status="ok")
