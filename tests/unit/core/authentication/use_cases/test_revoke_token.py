from dataclasses import dataclass
from types import TracebackType
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.authentication.services.refresh_session import (
    RefreshSessionService,
)
from fastapi_template.core.authentication.use_cases.revoke_token import RevokeTokenUseCase
from fastapi_template.core.health.repositories.health import HealthRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.repositories.user import UserRepository

_REFRESH_TOKEN = "refresh-token"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeUnitOfWork(UnitOfWork):
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
        raise UnexpectedRepositoryAccessError

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
async def test_revoke_token_uses_one_unit_of_work_for_revoke() -> None:
    user = _build_user()
    refresh_session_service = MagicMock(spec=RefreshSessionService)
    refresh_session_service.revoke_refresh_token = AsyncMock()
    uow = FakeUnitOfWork()
    use_case = RevokeTokenUseCase(
        _refresh_session_service=refresh_session_service,
        _uow=uow,
    )

    await use_case.execute(data=RefreshTokenDTO(refresh_token=_REFRESH_TOKEN), user=user)

    assert uow.entered_count == 1
    assert uow.exited_count == 1
    assert uow.rolled_back is False
    refresh_session_service.revoke_refresh_token.assert_awaited_once_with(
        uow=uow,
        refresh_token=_REFRESH_TOKEN,
        user=user,
    )


def _build_user() -> User:
    return User(
        id=1,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
    )
