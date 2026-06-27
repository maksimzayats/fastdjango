from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
from diwire import Container
from starlette import status
from starlette.websockets import WebSocketDisconnect

from modern_python_template.core.health.delivery.fastapi.schemas import HealthCheckResponseSchema
from modern_python_template.core.health.use_cases import SystemHealthUseCase
from tests.integration.factories import TestClientFactory


@pytest.mark.django_db(transaction=True)
class TestHealthController:
    """Tests for HealthController endpoints."""

    def test_health_check_success(
        self,
        container: Container,
    ) -> None:
        mock_use_case = self._override_health_use_case(container)
        test_client_factory = TestClientFactory(container=container)

        with test_client_factory() as test_client:
            response = test_client.get("/v1/health")

        response_data = HealthCheckResponseSchema.model_validate(response.json())
        assert response.status_code == HTTPStatus.OK
        assert response_data.status == "ok"
        mock_use_case.check.assert_awaited_once_with()

    def test_health_check_use_case_unavailable(
        self,
        container: Container,
    ) -> None:
        self._override_health_use_case(
            container,
            error=SystemHealthUseCase.HEALTH_CHECK_ERROR(),
        )
        test_client_factory = TestClientFactory(container=container)

        with test_client_factory() as test_client:
            response = test_client.get("/v1/health")

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json()["detail"] == "Service is unavailable"

    def test_health_check_websocket_success(
        self,
        container: Container,
    ) -> None:
        self._override_health_use_case(container)
        test_client_factory = TestClientFactory(container=container)

        with (
            test_client_factory() as test_client,
            test_client.websocket_connect("/v1/health/ws") as websocket,
        ):
            response_data = HealthCheckResponseSchema.model_validate(
                websocket.receive_json(),
            )

        assert response_data.status == "ok"

    def test_health_check_websocket_use_case_unavailable(
        self,
        container: Container,
    ) -> None:
        self._override_health_use_case(
            container,
            error=SystemHealthUseCase.HEALTH_CHECK_ERROR(),
        )
        test_client_factory = TestClientFactory(container=container)

        with (
            test_client_factory() as test_client,
            test_client.websocket_connect("/v1/health/ws") as websocket,
        ):
            assert websocket.receive_json() == {"status": "unavailable"}
            with pytest.raises(WebSocketDisconnect) as exc_info:
                websocket.receive_text()

        assert exc_info.value.code == status.WS_1011_INTERNAL_ERROR

    def _override_health_use_case(
        self,
        container: Container,
        *,
        error: Exception | None = None,
    ) -> MagicMock:
        mock_use_case = MagicMock(spec=SystemHealthUseCase)
        mock_use_case.check = AsyncMock(side_effect=error)
        container.add_instance(mock_use_case, provides=SystemHealthUseCase)

        return mock_use_case
