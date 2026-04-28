import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar, NamedTuple

from asgiref.sync import sync_to_async
from diwire import Injected
from django.db import models
from django.utils import timezone
from pydantic_settings import BaseSettings

from fastdjango.core.authentication.exceptions import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
)
from fastdjango.core.authentication.models import RefreshSession
from fastdjango.core.user.models import User
from fastdjango.foundation.services import BaseService
from fastdjango.foundation.transactions import TransactionFactory


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
    REFRESH_SESSION_NOT_FOUND_ERROR: ClassVar = RefreshSession.DoesNotExist

    _settings: Injected[RefreshSessionServiceSettings]
    _transaction_factory: Injected[TransactionFactory]

    async def create_refresh_session(
        self,
        *,
        user: User,
        user_agent: str,
        ip_address_trace: str | None,
    ) -> RefreshSessionResult:
        return await sync_to_async(
            self._create_refresh_session_transactionally,
            thread_sensitive=True,
        )(
            user=user,
            user_agent=user_agent,
            ip_address_trace=ip_address_trace,
        )

    async def rotate_refresh_token(self, *, refresh_token: str) -> RefreshSessionResult:
        return await sync_to_async(
            self._rotate_refresh_token_transactionally,
            thread_sensitive=True,
        )(refresh_token=refresh_token)

    async def revoke_refresh_token(
        self,
        *,
        refresh_token: str,
        user: User,
    ) -> None:
        await sync_to_async(
            self._revoke_refresh_token_transactionally,
            thread_sensitive=True,
        )(refresh_token=refresh_token, user=user)

    def _create_refresh_session_transactionally(
        self,
        *,
        user: User,
        user_agent: str,
        ip_address_trace: str | None,
    ) -> RefreshSessionResult:
        refresh_token = self._issue_refresh_token()
        refresh_token_hash = self._hash_refresh_token(refresh_token=refresh_token)

        with self._transaction_factory(
            span_name="create refresh session",
            service=type(self).__name__,
            method="_create_refresh_session_transactionally",
        ):
            session = RefreshSession.objects.create(
                user=user,
                refresh_token_hash=refresh_token_hash,
                user_agent=user_agent,
                ip_address_trace=ip_address_trace or "",
                expires_at=timezone.now() + self._settings.refresh_token_ttl,
            )

        return RefreshSessionResult(refresh_token=refresh_token, session=session)

    def _rotate_refresh_token_transactionally(
        self,
        *,
        refresh_token: str,
    ) -> RefreshSessionResult:
        new_refresh_token = self._issue_refresh_token()
        new_refresh_token_hash = self._hash_refresh_token(refresh_token=new_refresh_token)

        with self._transaction_factory(
            span_name="rotate refresh token",
            service=type(self).__name__,
            method="_rotate_refresh_token_transactionally",
        ):
            session = self._get_refresh_session_for_update(refresh_token=refresh_token)

            session.refresh_token_hash = new_refresh_token_hash
            session.rotation_counter += 1
            session.last_used_at = timezone.now()
            session.save(
                update_fields=[
                    "refresh_token_hash",
                    "rotation_counter",
                    "last_used_at",
                ],
            )

        return RefreshSessionResult(refresh_token=new_refresh_token, session=session)

    def _revoke_refresh_token_transactionally(
        self,
        *,
        refresh_token: str,
        user: User,
    ) -> None:
        with self._transaction_factory(
            span_name="revoke refresh token",
            service=type(self).__name__,
            method="_revoke_refresh_token_transactionally",
        ):
            session = self._get_refresh_session_for_update(refresh_token=refresh_token)
            if session.user.pk != user.pk:
                raise self.INVALID_REFRESH_TOKEN_ERROR

            session.revoked_at = timezone.now()
            session.save(update_fields=["revoked_at"])

    def _issue_refresh_token(self) -> str:
        return secrets.token_urlsafe(nbytes=self._settings.refresh_token_nbytes)

    def _hash_refresh_token(self, *, refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    def _get_refresh_session_for_update(
        self,
        *,
        refresh_token: str,
    ) -> RefreshSession:
        return self._get_active_refresh_session(
            refresh_token=refresh_token,
            for_update=True,
        )

    def _get_refresh_session_query(
        self,
        *,
        for_update: bool = False,
    ) -> models.QuerySet[RefreshSession]:
        queryset = RefreshSession.objects.select_related("user")
        if for_update:
            queryset = queryset.select_for_update()

        return queryset

    def _get_active_refresh_session(
        self,
        *,
        refresh_token: str,
        for_update: bool = False,
    ) -> RefreshSession:
        try:
            session = self._get_refresh_session_query(for_update=for_update).get(
                refresh_token_hash=self._hash_refresh_token(refresh_token=refresh_token),
            )
        except self.REFRESH_SESSION_NOT_FOUND_ERROR as e:
            raise self.INVALID_REFRESH_TOKEN_ERROR from e

        if not session.is_active:
            raise self.EXPIRED_REFRESH_TOKEN_ERROR

        return session


class RefreshSessionResult(NamedTuple):
    refresh_token: str
    session: RefreshSession
