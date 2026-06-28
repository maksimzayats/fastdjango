from unittest.mock import AsyncMock, MagicMock

import pytest
from diwire import Container
from starlette import status
from starlette.websockets import WebSocketDisconnect

from fastapi_template.core.health.delivery.fastapi.schemas.health import HealthCheckResponseSchema
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase
from tests.integration.factories import TestClientFactory


def test_health_check_websocket_success(container: Container) -> None:
    _override_health_use_case(container)
    test_client_factory = TestClientFactory(container=container)

    with (
        test_client_factory() as test_client,
        test_client.websocket_connect("/api/v1/health/ws") as websocket,
    ):
        response_data = HealthCheckResponseSchema.model_validate(
            websocket.receive_json(),
        )

    assert response_data.status == "ok"


def test_health_check_websocket_use_case_unavailable(container: Container) -> None:
    _override_health_use_case(
        container,
        error=SystemHealthUseCase.HEALTH_CHECK_ERROR(),
    )
    test_client_factory = TestClientFactory(container=container)

    with (
        test_client_factory() as test_client,
        test_client.websocket_connect("/api/v1/health/ws") as websocket,
    ):
        assert websocket.receive_json() == {"status": "unavailable"}
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()

    assert exc_info.value.code == status.WS_1011_INTERNAL_ERROR


def _override_health_use_case(
    container: Container,
    *,
    error: Exception | None = None,
) -> MagicMock:
    mock_use_case = MagicMock(spec=SystemHealthUseCase)
    mock_use_case.execute = AsyncMock(side_effect=error)
    container.add_instance(mock_use_case, provides=SystemHealthUseCase)

    return mock_use_case
