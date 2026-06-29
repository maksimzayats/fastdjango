import pytest
from diwire import Container

from fastapi_template.core.health.services.database_health_checker import (
    DatabaseHealthChecker,
)


@pytest.mark.anyio
async def test_database_health_checker_checks_database(container: Container) -> None:
    health_checker = container.resolve(DatabaseHealthChecker)

    await health_checker.check_database()
