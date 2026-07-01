from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from starlette import status
from starlette.websockets import WebSocketDisconnect

from fastapi_template.core.health.delivery.fastapi.schemas.health import HealthCheckResponseSchema
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase
from tests.integration.factories import TestClientFactory


def test_health_check_websocket_success(
    test_client_factory: TestClientFactory,
    health_use_case_override: Callable[..., MagicMock],
) -> None:
    health_use_case_override()
    with (
        test_client_factory() as test_client,
        test_client.websocket_connect("/api/v1/health/ws") as websocket,
    ):
        response_data = HealthCheckResponseSchema.model_validate(
            websocket.receive_json(),
        )

    assert response_data.status == "ok"


def test_health_check_websocket_use_case_unavailable(
    test_client_factory: TestClientFactory,
    health_use_case_override: Callable[..., MagicMock],
) -> None:
    health_use_case_override(
        error=SystemHealthUseCase.HEALTH_CHECK_ERROR(),
    )
    with (
        test_client_factory() as test_client,
        test_client.websocket_connect("/api/v1/health/ws") as websocket,
    ):
        assert websocket.receive_json() == {"status": "unavailable"}
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()

    assert exc_info.value.code == status.WS_1011_INTERNAL_ERROR
