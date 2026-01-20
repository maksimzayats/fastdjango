from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from core.health.services import HealthCheckError, HealthService
from delivery.http.controllers.health.controllers import HealthCheckResponseSchema
from infrastructure.frameworks.punq.auto_registering import AutoRegisteringContainer
from tests.integration.factories import TestClientFactory


@pytest.mark.django_db(transaction=True)
class TestHealthController:
    """Tests for HealthController endpoints."""

    def test_health_check_success(
        self,
        test_client_factory: TestClientFactory,
    ) -> None:
        with test_client_factory() as test_client:
            response = test_client.get("/v1/health")

        response_data = HealthCheckResponseSchema.model_validate(response.json())
        assert response.status_code == HTTPStatus.OK
        assert response_data.status == "ok"

    def test_health_check_service_unavailable(
        self,
        container: AutoRegisteringContainer,
    ) -> None:
        mock_service = MagicMock(spec=HealthService)
        mock_service.check_system_health.side_effect = HealthCheckError()
        container.register(HealthService, instance=mock_service)

        test_client_factory = TestClientFactory(container=container)

        with test_client_factory() as test_client:
            response = test_client.get("/v1/health")

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json()["detail"] == "Service is unavailable"
