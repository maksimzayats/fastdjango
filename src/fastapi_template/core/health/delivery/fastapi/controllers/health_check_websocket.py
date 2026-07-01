from dataclasses import dataclass

from diwire import Injected
from fastapi import APIRouter, WebSocket
from starlette import status

from fastapi_template.core.health.delivery.fastapi.schemas.health import HealthCheckResponseSchema
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class HealthCheckWebSocketController(BaseAsyncController):
    """Register the websocket health-check endpoint."""

    _system_health_use_case: Injected[SystemHealthUseCase]

    def register(self, registry: APIRouter) -> None:
        """Register the controller routes."""
        registry.add_api_websocket_route(
            path="/api/v1/health/ws",
            endpoint=self.health_check_websocket,
        )

    async def health_check_websocket(self, websocket: WebSocket) -> None:
        """Send websocket readiness status and close the connection."""
        await websocket.accept()

        try:
            await self._system_health_use_case.execute()
        except SystemHealthUseCase.HEALTH_CHECK_ERROR:
            await websocket.send_json({"status": "unavailable"})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        await websocket.send_json(HealthCheckResponseSchema(status="ok").model_dump())
        await websocket.close()
