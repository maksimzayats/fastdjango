import pytest
from diwire import Container

from fastapi_template.core.unit_of_work import UnitOfWork


@pytest.mark.anyio
async def test_health_repository_checks_database(container: Container) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        await active_uow.health_repository.check_database()
