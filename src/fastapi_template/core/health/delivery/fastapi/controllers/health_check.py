from dataclasses import dataclass
from http import HTTPStatus

from diwire import Injected
from fastapi import APIRouter, HTTPException

from fastapi_template.core.health.delivery.fastapi.schemas.health import HealthCheckResponseSchema
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class HealthCheckController(BaseAsyncController):
    """Register the HTTP health-check endpoint."""

    _system_health_use_case: Injected[SystemHealthUseCase]

    def register(self, registry: APIRouter) -> None:
        """Register the controller routes."""
        registry.add_api_route(
            path="/api/v1/health",
            endpoint=self.health_check,
            methods=["GET"],
            response_model=HealthCheckResponseSchema,
        )

    async def health_check(self) -> HealthCheckResponseSchema:
        """Return service readiness after the database health use case succeeds.

        Returns:
            The health-check response.

        Raises:
            HTTPException: If the service is unavailable.
        """
        try:
            await self._system_health_use_case.execute()
        except SystemHealthUseCase.HEALTH_CHECK_ERROR as exception:
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Service is unavailable",
            ) from exception

        return HealthCheckResponseSchema(status="ok")
