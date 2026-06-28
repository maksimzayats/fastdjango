from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

from diwire import Container

from fastapi_template.core.health.delivery.fastapi.schemas.health import HealthCheckResponseSchema
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase
from tests.integration.factories import TestClientFactory


def test_health_check_success(container: Container) -> None:
    mock_use_case = _override_health_use_case(container)
    test_client_factory = TestClientFactory(container=container)

    with test_client_factory() as test_client:
        response = test_client.get("/api/v1/health")

    response_data = HealthCheckResponseSchema.model_validate(response.json())
    assert response.status_code == HTTPStatus.OK
    assert response_data.status == "ok"
    mock_use_case.execute.assert_awaited_once_with()


def test_health_check_use_case_unavailable(container: Container) -> None:
    _override_health_use_case(
        container,
        error=SystemHealthUseCase.HEALTH_CHECK_ERROR(),
    )
    test_client_factory = TestClientFactory(container=container)

    with test_client_factory() as test_client:
        response = test_client.get("/api/v1/health")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Service is unavailable"


def _override_health_use_case(
    container: Container,
    *,
    error: Exception | None = None,
) -> MagicMock:
    mock_use_case = MagicMock(spec=SystemHealthUseCase)
    mock_use_case.execute = AsyncMock(side_effect=error)
    container.add_instance(mock_use_case, provides=SystemHealthUseCase)

    return mock_use_case
