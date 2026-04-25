import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import NamedTuple

from django.db import models, transaction
from django.utils import timezone
from pydantic_settings import BaseSettings

from fastdjango.core.authentication.exceptions import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
)
from fastdjango.core.authentication.models import RefreshSession
from fastdjango.core.user.models import User
from fastdjango.foundation.services import BaseService


class RefreshSessionServiceSettings(BaseSettings):
    refresh_token_nbytes: int = 32
    refresh_token_ttl_days: int = 30

    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_token_ttl_days)


@dataclass(kw_only=True)
class RefreshSessionService(BaseService):
    _settings: RefreshSessionServiceSettings

    def create_refresh_session(
        self,
        user: User,
        user_agent: str,
        ip_address_trace: str | None,
    ) -> RefreshSessionResult:
        refresh_token = self._issue_refresh_token()
        refresh_token_hash = self._hash_refresh_token(refresh_token)

        session = RefreshSession.objects.create(
            user=user,
            refresh_token_hash=refresh_token_hash,
            user_agent=user_agent,
            ip_address_trace=ip_address_trace or "",
            expires_at=timezone.now() + self._settings.refresh_token_ttl,
        )

        return RefreshSessionResult(refresh_token=refresh_token, session=session)

    @transaction.atomic
    def rotate_refresh_token(self, refresh_token: str) -> RefreshSessionResult:
        session = self._get_refresh_session_for_update(refresh_token)

        new_refresh_token = self._issue_refresh_token()
        session.refresh_token_hash = self._hash_refresh_token(new_refresh_token)
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

    @transaction.atomic
    def revoke_refresh_token(
        self,
        refresh_token: str,
        user: User,
    ) -> None:
        session = self._get_refresh_session_for_update(refresh_token)
        if session.user.pk != user.pk:
            raise InvalidRefreshTokenError

        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])

    def _issue_refresh_token(self) -> str:
        return secrets.token_urlsafe(nbytes=self._settings.refresh_token_nbytes)

    def _hash_refresh_token(self, refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    def _get_refresh_session_for_update(
        self,
        refresh_token: str,
    ) -> RefreshSession:
        return self._get_active_refresh_session(
            refresh_token,
            for_update=True,
        )

    def _get_refresh_session_query(
        self,
        *,
        for_update: bool = False,
    ) -> models.QuerySet[RefreshSession]:
        queryset = RefreshSession.objects.all()
        if for_update:
            queryset = queryset.select_for_update()

        return queryset

    def _get_active_refresh_session(
        self,
        refresh_token: str,
        *,
        for_update: bool = False,
    ) -> RefreshSession:
        try:
            session = self._get_refresh_session_query(for_update=for_update).get(
                refresh_token_hash=self._hash_refresh_token(refresh_token),
            )
        except RefreshSession.DoesNotExist as e:
            raise InvalidRefreshTokenError from e

        if not session.is_active:
            raise ExpiredRefreshTokenError

        return session


class RefreshSessionResult(NamedTuple):
    refresh_token: str
    session: RefreshSession
