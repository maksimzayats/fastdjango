import logging
from dataclasses import dataclass
from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from fastdjango.core.health.delivery.fastapi.schemas import HealthCheckResponseSchema
from fastdjango.core.health.use_cases import SystemHealthUseCase
from fastdjango.foundation.delivery.controllers import BaseController

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class HealthController(BaseController):
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
        except SystemHealthUseCase.HEALTH_CHECK_ERROR as e:
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Service is unavailable",
            ) from e

        return HealthCheckResponseSchema(status="ok")
