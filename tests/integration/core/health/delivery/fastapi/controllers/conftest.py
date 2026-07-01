from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from diwire import Container

from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase

HealthUseCaseOverride = Callable[..., MagicMock]


@pytest.fixture(scope="function")
def health_use_case_override(container: Container) -> HealthUseCaseOverride:
    def override(*, error: Exception | None = None) -> MagicMock:
        mock_use_case = MagicMock(spec=SystemHealthUseCase)
        mock_use_case.execute = AsyncMock(side_effect=error)
        container.add_instance(mock_use_case, provides=SystemHealthUseCase)

        return mock_use_case

    return override
