import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import TracebackType
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.entities.refresh_session import RefreshSession
from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.authentication.services.refresh_session import (
    RefreshSessionResult,
    RefreshSessionService,
)
from fastapi_template.core.authentication.use_cases.refresh_token import RefreshTokenUseCase
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.repositories.user import UserRepository

_ACCESS_TOKEN = "access-token"  # noqa: S105
_REFRESH_TOKEN = "refresh-token"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105
_REFRESH_TOKEN_HASH = "refresh-token-hash"  # noqa: S105


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
async def test_refresh_token_uses_one_unit_of_work_for_rotation() -> None:
    user = _build_user()
    refresh_session_result = RefreshSessionResult(
        refresh_token=_REFRESH_TOKEN,
        session=_build_refresh_session(user=user),
    )
    refresh_session_service = MagicMock(spec=RefreshSessionService)
    refresh_session_service.rotate_refresh_token = AsyncMock(
        return_value=refresh_session_result,
    )
    jwt_service = MagicMock(spec=JWTService)
    jwt_service.issue_access_token.return_value = _ACCESS_TOKEN
    uow = FakeUnitOfWork()
    use_case = RefreshTokenUseCase(
        _jwt_service=jwt_service,
        _refresh_session_service=refresh_session_service,
        _uow=uow,
    )

    result = await use_case.execute(data=RefreshTokenDTO(refresh_token=_REFRESH_TOKEN))

    assert result.access_token == _ACCESS_TOKEN
    assert result.refresh_token == refresh_session_result.refresh_token
    assert uow.entered_count == 1
    assert uow.exited_count == 1
    assert uow.rolled_back is False
    refresh_session_service.rotate_refresh_token.assert_awaited_once_with(
        uow=uow,
        refresh_token=_REFRESH_TOKEN,
    )


@pytest.mark.anyio
async def test_refresh_token_rolls_back_when_access_token_signing_fails() -> None:
    user = _build_user()
    refresh_session_service = MagicMock(spec=RefreshSessionService)
    refresh_session_service.rotate_refresh_token = AsyncMock(
        return_value=RefreshSessionResult(
            refresh_token=_REFRESH_TOKEN,
            session=_build_refresh_session(user=user),
        ),
    )
    jwt_service = MagicMock(spec=JWTService)
    jwt_service.issue_access_token.side_effect = RuntimeError("signing failed")
    uow = FakeUnitOfWork()
    use_case = RefreshTokenUseCase(
        _jwt_service=jwt_service,
        _refresh_session_service=refresh_session_service,
        _uow=uow,
    )

    with pytest.raises(RuntimeError, match="signing failed"):
        await use_case.execute(data=RefreshTokenDTO(refresh_token=_REFRESH_TOKEN))

    assert uow.entered_count == 1
    assert uow.exited_count == 1
    assert uow.rolled_back is True


@pytest.mark.anyio
async def test_refresh_token_rolls_back_for_inactive_session_user() -> None:
    user = _build_user(is_active=False)
    refresh_session_service = MagicMock(spec=RefreshSessionService)
    refresh_session_service.rotate_refresh_token = AsyncMock(
        return_value=RefreshSessionResult(
            refresh_token=_REFRESH_TOKEN,
            session=_build_refresh_session(user=user),
        ),
    )
    jwt_service = MagicMock(spec=JWTService)
    uow = FakeUnitOfWork()
    use_case = RefreshTokenUseCase(
        _jwt_service=jwt_service,
        _refresh_session_service=refresh_session_service,
        _uow=uow,
    )

    with pytest.raises(RefreshTokenUseCase.INVALID_REFRESH_TOKEN_ERROR):
        await use_case.execute(data=RefreshTokenDTO(refresh_token=_REFRESH_TOKEN))

    assert uow.entered_count == 1
    assert uow.exited_count == 1
    assert uow.rolled_back is True
    jwt_service.issue_access_token.assert_not_called()


def _build_user(*, is_active: bool = True) -> User:
    return User(
        id=1,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
        is_active=is_active,
    )


def _build_refresh_session(*, user: User) -> RefreshSession:
    return RefreshSession(
        id=uuid.uuid7(),
        refresh_token_hash=_REFRESH_TOKEN_HASH,
        user=user,
        user_agent="test",
        ip_address_trace="127.0.0.1",
        created_at=datetime.now(tz=UTC),
        expires_at=datetime.now(tz=UTC) + timedelta(days=30),
    )
