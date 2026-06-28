import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar, NamedTuple

from diwire import Injected
from pydantic_settings import BaseSettings

from fastapi_template.core.authentication.dtos import CreateRefreshSessionDTO
from fastapi_template.core.authentication.entities import RefreshSession
from fastapi_template.core.authentication.exceptions import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
)
from fastapi_template.core.authentication.repositories import RefreshSessionRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities import User
from fastapi_template.foundation.services import BaseService


class RefreshSessionServiceSettings(BaseSettings):
    refresh_token_nbytes: int = 32
    refresh_token_ttl_days: int = 30

    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_token_ttl_days)


@dataclass(kw_only=True)
class RefreshSessionService(BaseService):
    INVALID_REFRESH_TOKEN_ERROR: ClassVar = InvalidRefreshTokenError
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = ExpiredRefreshTokenError

    _settings: Injected[RefreshSessionServiceSettings]

    async def create_refresh_session(
        self,
        *,
        uow: UnitOfWork,
        user: User,
        user_agent: str,
        ip_address_trace: str | None,
    ) -> RefreshSessionResult:
        refresh_token = self._issue_refresh_token()
        session = await uow.refresh_session_repository.create(
            data=CreateRefreshSessionDTO(
                user=user,
                refresh_token_hash=self._hash_refresh_token(refresh_token=refresh_token),
                user_agent=user_agent,
                ip_address_trace=ip_address_trace or "",
                expires_at=datetime.now(tz=UTC) + self._settings.refresh_token_ttl,
            ),
        )
        return RefreshSessionResult(refresh_token=refresh_token, session=session)

    async def rotate_refresh_token(
        self,
        *,
        uow: UnitOfWork,
        refresh_token: str,
    ) -> RefreshSessionResult:
        session = await self._get_active_refresh_session(
            repository=uow.refresh_session_repository,
            refresh_token=refresh_token,
        )
        new_refresh_token = self._issue_refresh_token()
        rotated_session = await uow.refresh_session_repository.replace_token_hash(
            session_id=session.id,
            refresh_token_hash=self._hash_refresh_token(refresh_token=new_refresh_token),
            last_used_at=datetime.now(tz=UTC),
            rotation_counter=session.rotation_counter + 1,
        )
        if rotated_session is None:
            raise self.INVALID_REFRESH_TOKEN_ERROR

        return RefreshSessionResult(refresh_token=new_refresh_token, session=rotated_session)

    async def revoke_refresh_token(
        self,
        *,
        uow: UnitOfWork,
        refresh_token: str,
        user: User,
    ) -> None:
        session = await self._get_active_refresh_session(
            repository=uow.refresh_session_repository,
            refresh_token=refresh_token,
        )
        if session.user.id != user.id:
            raise self.INVALID_REFRESH_TOKEN_ERROR

        await uow.refresh_session_repository.revoke(
            session_id=session.id,
            revoked_at=datetime.now(tz=UTC),
        )

    def _issue_refresh_token(self) -> str:
        return secrets.token_urlsafe(nbytes=self._settings.refresh_token_nbytes)

    def _hash_refresh_token(self, *, refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    async def _get_active_refresh_session(
        self,
        *,
        repository: RefreshSessionRepository,
        refresh_token: str,
    ) -> RefreshSession:
        session = await repository.get_by_token_hash(
            refresh_token_hash=self._hash_refresh_token(refresh_token=refresh_token),
        )
        if session is None:
            raise self.INVALID_REFRESH_TOKEN_ERROR

        if not session.is_active:
            raise self.EXPIRED_REFRESH_TOKEN_ERROR

        return session


class RefreshSessionResult(NamedTuple):
    refresh_token: str
    session: RefreshSession
