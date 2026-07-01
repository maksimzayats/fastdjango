from collections.abc import Callable
from http import HTTPStatus
from unittest.mock import MagicMock

from fastapi_template.core.health.delivery.fastapi.schemas.health import HealthCheckResponseSchema
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase
from tests.integration.factories import TestClientFactory


def test_health_check_success(
    test_client_factory: TestClientFactory,
    health_use_case_override: Callable[..., MagicMock],
) -> None:
    mock_use_case = health_use_case_override()
    with test_client_factory() as test_client:
        response = test_client.get("/api/v1/health")

    response_data = HealthCheckResponseSchema.model_validate(response.json())
    assert response.status_code == HTTPStatus.OK
    assert response_data.status == "ok"
    mock_use_case.execute.assert_awaited_once_with()


def test_health_check_use_case_unavailable(
    test_client_factory: TestClientFactory,
    health_use_case_override: Callable[..., MagicMock],
) -> None:
    health_use_case_override(
        error=SystemHealthUseCase.HEALTH_CHECK_ERROR(),
    )
    with test_client_factory() as test_client:
        response = test_client.get("/api/v1/health")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Service is unavailable"
