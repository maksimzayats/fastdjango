import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import TracebackType

import pytest

from fastapi_template.core.authentication.dtos.create_refresh_session import (
    CreateRefreshSessionDTO,
)
from fastapi_template.core.authentication.dtos.replace_refresh_session_token import (
    ReplaceRefreshSessionTokenDTO,
)
from fastapi_template.core.authentication.entities.refresh_session import RefreshSession
from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.authentication.services.refresh_session import (
    RefreshSessionService,
    RefreshSessionServiceSettings,
)
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.repositories.user import UserRepository

_OLD_REFRESH_TOKEN = "old-refresh-token"  # noqa: S105


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeRefreshSessionRepository(RefreshSessionRepository):
    session: RefreshSession | None
    replace_returns_none: bool = False
    replaced_expected_hash: str | None = None
    replaced_hash: str | None = None
    replaced_session_id: uuid.UUID | None = None
    replaced_rotation_counter: int | None = None
    revoked_session_id: uuid.UUID | None = None

    async def create(self, *, data: CreateRefreshSessionDTO) -> RefreshSession:
        self.session = _build_session(
            session_id=data.id,
            user=data.user,
            refresh_token_hash=data.refresh_token_hash,
            created_at=data.created_at,
            last_used_at=data.last_used_at,
            expires_at=data.expires_at,
            revoked_at=data.revoked_at,
            rotation_counter=data.rotation_counter,
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
        data: ReplaceRefreshSessionTokenDTO,
    ) -> RefreshSession | None:
        self.replaced_session_id = data.session_id
        self.replaced_expected_hash = data.expected_refresh_token_hash
        self.replaced_hash = data.refresh_token_hash
        self.replaced_rotation_counter = data.rotation_counter
        if (
            self.replace_returns_none
            or self.session is None
            or self.session.id != data.session_id
            or self.session.refresh_token_hash != data.expected_refresh_token_hash
        ):
            return None

        self.session = _build_session(
            session_id=self.session.id,
            user=self.session.user,
            refresh_token_hash=data.refresh_token_hash,
            rotation_counter=data.rotation_counter,
            last_used_at=data.last_used_at,
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

    assert repository.replaced_expected_hash == session.refresh_token_hash
    assert repository.replaced_hash is not None
    assert repository.replaced_hash != session.refresh_token_hash
    assert repository.replaced_session_id == session.id
    assert repository.replaced_rotation_counter == session.rotation_counter + 1
    assert result.session.rotation_counter == 1


@pytest.mark.anyio
async def test_rotate_refresh_token_rejects_missing_session() -> None:
    repository = FakeRefreshSessionRepository(session=None)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    with pytest.raises(RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR):
        await service.rotate_refresh_token(
            uow=uow,
            refresh_token=_OLD_REFRESH_TOKEN,
        )


@pytest.mark.anyio
async def test_rotate_refresh_token_rejects_failed_token_replacement() -> None:
    session = _build_session()
    repository = FakeRefreshSessionRepository(session=session, replace_returns_none=True)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    with pytest.raises(RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR):
        await service.rotate_refresh_token(
            uow=uow,
            refresh_token=_OLD_REFRESH_TOKEN,
        )


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
    assert repository.session.id.version == 7
    assert repository.session.created_at < repository.session.expires_at
    assert repository.session.last_used_at is None
    assert repository.session.ip_address_trace == ""
    assert repository.session.revoked_at is None
    assert repository.session.rotation_counter == 0
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
async def test_revoke_refresh_token_rejects_session_for_another_user() -> None:
    session = _build_session()
    repository = FakeRefreshSessionRepository(session=session)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    with pytest.raises(RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR):
        await service.revoke_refresh_token(
            uow=uow,
            refresh_token=_OLD_REFRESH_TOKEN,
            user=_build_user(user_id=2),
        )


@pytest.mark.anyio
async def test_revoke_refresh_token_rejects_missing_session() -> None:
    repository = FakeRefreshSessionRepository(session=None)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    with pytest.raises(RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR):
        await service.revoke_refresh_token(
            uow=uow,
            refresh_token=_OLD_REFRESH_TOKEN,
            user=_build_user(),
        )


@pytest.mark.anyio
async def test_revoke_refresh_token_rejects_expired_session() -> None:
    session = _build_session(expires_at=datetime.now(tz=UTC) - timedelta(seconds=1))
    repository = FakeRefreshSessionRepository(session=session)
    uow = FakeUnitOfWork(_refresh_session_repository=repository)
    service = _build_service()

    with pytest.raises(RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR):
        await service.revoke_refresh_token(
            uow=uow,
            refresh_token=_OLD_REFRESH_TOKEN,
            user=session.user,
        )


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


@pytest.mark.anyio
async def test_refresh_token_rejects_revoked_sessions() -> None:
    repository = FakeRefreshSessionRepository(
        session=_build_session(revoked_at=datetime.now(tz=UTC)),
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


def _build_user(*, user_id: int = 1) -> User:
    return User(
        id=user_id,
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
    created_at: datetime | None = None,
    rotation_counter: int = 0,
    last_used_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> RefreshSession:
    session_created_at = created_at or datetime.now(tz=UTC)
    return RefreshSession(
        id=session_id or uuid.uuid7(),
        refresh_token_hash=refresh_token_hash
        or hashlib.sha256(_OLD_REFRESH_TOKEN.encode()).hexdigest(),
        user=user or _build_user(),
        user_agent=user_agent,
        ip_address_trace=ip_address_trace,
        created_at=session_created_at,
        last_used_at=last_used_at,
        expires_at=expires_at or session_created_at + timedelta(days=30),
        revoked_at=revoked_at,
        rotation_counter=rotation_counter,
    )


def _stored_secret_hash() -> str:
    return "hash"
