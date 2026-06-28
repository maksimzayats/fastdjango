from dataclasses import dataclass
from types import TracebackType

import pytest

from fastapi_template.core.authentication.repositories import RefreshSessionRepository
from fastapi_template.core.health.repositories import HealthRepository
from fastapi_template.core.health.use_cases import SystemHealthUseCase
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.repositories import UserRepository


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeHealthRepository(HealthRepository):
    error: Exception | None = None
    called: bool = False

    async def check_database(self) -> None:
        self.called = True
        if self.error is not None:
            raise self.error


@dataclass
class FakeUnitOfWork(UnitOfWork):
    _health_repository: HealthRepository
    entered_count: int = 0
    exited_count: int = 0
    rolled_back: bool = False

    @property
    def user_repository(self) -> UserRepository:
        raise UnexpectedRepositoryAccessError

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        raise UnexpectedRepositoryAccessError

    @property
    def health_repository(self) -> HealthRepository:
        return self._health_repository

    async def __aenter__(self) -> UnitOfWork:
        self.entered_count += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self.exited_count += 1
        self.rolled_back = exc_type is not None
        return None


@pytest.mark.anyio
async def test_health_check_checks_database() -> None:
    health_repository = FakeHealthRepository()
    use_case = SystemHealthUseCase(_uow=FakeUnitOfWork(_health_repository=health_repository))

    await use_case.execute()

    assert health_repository.called is True


@pytest.mark.anyio
async def test_health_check_maps_database_errors_to_health_check_error() -> None:
    health_repository = FakeHealthRepository(error=RuntimeError("database unavailable"))
    use_case = SystemHealthUseCase(_uow=FakeUnitOfWork(_health_repository=health_repository))

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.execute()
