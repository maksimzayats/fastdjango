from dataclasses import dataclass

import pytest

from fastapi_template.core.health.services.database_health_checker import (
    DatabaseHealthChecker,
)
from fastapi_template.core.health.use_cases.system_health import SystemHealthUseCase


@dataclass
class FakeDatabaseHealthChecker(DatabaseHealthChecker):
    error: Exception | None = None
    called: bool = False

    async def check_database(self) -> None:
        self.called = True
        if self.error is not None:
            raise self.error


@pytest.mark.anyio
async def test_health_check_checks_database() -> None:
    health_checker = FakeDatabaseHealthChecker()
    use_case = SystemHealthUseCase(_database_health_checker=health_checker)

    await use_case.execute()

    assert health_checker.called is True


@pytest.mark.anyio
async def test_health_check_maps_database_errors_to_health_check_error() -> None:
    health_checker = FakeDatabaseHealthChecker(error=RuntimeError("database unavailable"))
    use_case = SystemHealthUseCase(_database_health_checker=health_checker)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.execute()
