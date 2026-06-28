import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import TracebackType

import pytest

from fastapi_template.core.authentication.dtos import CreateRefreshSessionDTO
from fastapi_template.core.authentication.entities import RefreshSession
from fastapi_template.core.authentication.repositories import RefreshSessionRepository
from fastapi_template.core.authentication.services.refresh_session import (
    RefreshSessionService,
    RefreshSessionServiceSettings,
)
from fastapi_template.core.health.repositories import HealthRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.repositories import UserRepository

_OLD_REFRESH_TOKEN = "old-refresh-token"  # noqa: S105


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeRefreshSessionRepository(RefreshSessionRepository):
    session: RefreshSession | None
    replaced_session_id: uuid.UUID | None = None
    replaced_hash: str | None = None
    replaced_rotation_counter: int | None = None
    revoked_session_id: uuid.UUID | None = None

    async def create(self, *, data: CreateRefreshSessionDTO) -> RefreshSession:
        self.session = _build_session(
            user=data.user,
            refresh_token_hash=data.refresh_token_hash,
            expires_at=data.expires_at,
            user_agent=data.user_agent,
            ip_address_trace=data.ip_address_trace,
        )
        return self.session

    async def get_by_token_hash(self, *, refresh_token_hash: str) -> RefreshSession | None:
        expected_hash = hashlib.sha256(_OLD_REFRESH_TOKEN.encode()).hexdigest()
        if refresh_token_hash != expected_hash:
            return None

        return self.session

    async def replace_token_hash(
        self,
        *,
        session_id: uuid.UUID,
        refresh_token_hash: str,
        last_used_at: datetime,
        rotation_counter: int,
    ) -> RefreshSession | None:
        self.replaced_session_id = session_id
        self.replaced_hash = refresh_token_hash
        self.replaced_rotation_counter = rotation_counter
        if self.session is None:
            return None

        self.session = _build_session(
            session_id=session_id,
            refresh_token_hash=refresh_token_hash,
            rotation_counter=rotation_counter,
            last_used_at=last_used_at,
        )
        return self.session

    async def revoke(self, *, session_id: uuid.UUID, revoked_at: datetime) -> None:
        self.revoked_session_id = session_id
        if self.session is None:
            return

        self.session = _build_session(
            session_id=session_id,
            refresh_token_hash=self.session.refresh_token_hash,
            revoked_at=revoked_at,
        )


@dataclass
class FakeUnitOfWork(UnitOfWork):
    _refresh_session_repository: RefreshSessionRepository
    entered_count: int = 0
    exited_count: int = 0
    rolled_back: bool = False

    @property
    def user_repository(self) -> UserRepository:
        raise UnexpectedRepositoryAccessError

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        return self._refresh_session_repository

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
async def test_rotate_refresh_token_replaces_stored_hash() -> None:
    session = _build_session()
    repository = FakeRefreshSessionRepository(session=session)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    result = await service.rotate_refresh_token(
        uow=uow,
        refresh_token=_OLD_REFRESH_TOKEN,
    )

    assert repository.replaced_session_id == session.id
    assert repository.replaced_hash is not None
    assert repository.replaced_hash != session.refresh_token_hash
    assert repository.replaced_rotation_counter == session.rotation_counter + 1
    assert result.session.rotation_counter == 1


@pytest.mark.anyio
async def test_create_refresh_session_uses_active_unit_of_work() -> None:
    repository = FakeRefreshSessionRepository(session=None)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()
    user = _build_user()

    result = await service.create_refresh_session(
        uow=uow,
        user=user,
        user_agent="test-agent",
        ip_address_trace=None,
    )

    assert result.session.user == user
    assert result.refresh_token
    assert repository.session is not None
    assert repository.session.ip_address_trace == ""
    assert uow.entered_count == 0
    assert uow.exited_count == 0


@pytest.mark.anyio
async def test_revoke_refresh_token_marks_matching_session_revoked() -> None:
    session = _build_session()
    repository = FakeRefreshSessionRepository(session=session)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    await service.revoke_refresh_token(
        uow=uow,
        refresh_token=_OLD_REFRESH_TOKEN,
        user=session.user,
    )

    assert repository.revoked_session_id == session.id


@pytest.mark.anyio
async def test_refresh_token_rejects_expired_sessions() -> None:
    repository = FakeRefreshSessionRepository(
        session=_build_session(expires_at=datetime.now(tz=UTC) - timedelta(seconds=1)),
    )
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    with pytest.raises(RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR):
        await service.rotate_refresh_token(
            uow=uow,
            refresh_token=_OLD_REFRESH_TOKEN,
        )


def _build_service() -> RefreshSessionService:
    return RefreshSessionService(_settings=RefreshSessionServiceSettings())


def _build_user() -> User:
    return User(
        id=1,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_stored_secret_hash(),
    )


def _build_session(
    *,
    session_id: uuid.UUID | None = None,
    user: User | None = None,
    refresh_token_hash: str | None = None,
    expires_at: datetime | None = None,
    user_agent: str = "test-agent",
    ip_address_trace: str = "127.0.0.1",
    rotation_counter: int = 0,
    last_used_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> RefreshSession:
    return RefreshSession(
        id=session_id or uuid.uuid7(),
        refresh_token_hash=refresh_token_hash
        or hashlib.sha256(_OLD_REFRESH_TOKEN.encode()).hexdigest(),
        user=user or _build_user(),
        user_agent=user_agent,
        ip_address_trace=ip_address_trace,
        created_at=datetime.now(tz=UTC),
        last_used_at=last_used_at,
        expires_at=expires_at or datetime.now(tz=UTC) + timedelta(days=30),
        revoked_at=revoked_at,
        rotation_counter=rotation_counter,
    )


def _stored_secret_hash() -> str:
    return "hash"
