import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar, NamedTuple

from diwire import Injected
from pydantic_settings import BaseSettings

from fastapi_template.core.authentication.dtos.create_refresh_session import (
    CreateRefreshSessionDTO,
)
from fastapi_template.core.authentication.dtos.replace_refresh_session_token import (
    ReplaceRefreshSessionTokenDTO,
)
from fastapi_template.core.authentication.entities.refresh_session import RefreshSession
from fastapi_template.core.authentication.exceptions.expired_refresh_token import (
    ExpiredRefreshTokenError,
)
from fastapi_template.core.authentication.exceptions.invalid_refresh_token import (
    InvalidRefreshTokenError,
)
from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.foundation.service import BaseService


class RefreshSessionServiceSettings(BaseSettings):
    """Define RefreshSessionServiceSettings."""

    refresh_token_nbytes: int = 32
    refresh_token_ttl_days: int = 30

    @property
    def refresh_token_ttl(self) -> timedelta:
        """Run refresh token ttl.

        Returns:
        The operation result.
        """
        return timedelta(days=self.refresh_token_ttl_days)


@dataclass(kw_only=True)
class RefreshSessionService(BaseService):
    """Define RefreshSessionService."""

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
        """Run create refresh session.

        Returns:
        The operation result.
        """
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
        """Run rotate refresh token.

        Returns:
        The operation result.
        """
        expected_refresh_token_hash = self._hash_refresh_token(refresh_token=refresh_token)
        session = await self._get_active_refresh_session(
            repository=uow.refresh_session_repository,
            refresh_token_hash=expected_refresh_token_hash,
        )
        new_refresh_token = self._issue_refresh_token()
        rotated_session = await uow.refresh_session_repository.replace_token_hash(
            data=ReplaceRefreshSessionTokenDTO(
                session_id=session.id,
                expected_refresh_token_hash=expected_refresh_token_hash,
                refresh_token_hash=self._hash_refresh_token(refresh_token=new_refresh_token),
                last_used_at=datetime.now(tz=UTC),
                rotation_counter=session.rotation_counter + 1,
            ),
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
        """Run revoke refresh token."""
        session = await self._get_active_refresh_session(
            repository=uow.refresh_session_repository,
            refresh_token_hash=self._hash_refresh_token(refresh_token=refresh_token),
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
        refresh_token_hash: str,
    ) -> RefreshSession:
        session = await repository.get_by_token_hash(
            refresh_token_hash=refresh_token_hash,
        )
        if session is None:
            raise self.INVALID_REFRESH_TOKEN_ERROR

        if not session.is_active:
            raise self.EXPIRED_REFRESH_TOKEN_ERROR

        return session


class RefreshSessionResult(NamedTuple):
    """Define RefreshSessionResult."""

    refresh_token: str
    session: RefreshSession
