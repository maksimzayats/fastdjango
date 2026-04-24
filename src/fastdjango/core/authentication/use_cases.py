from dataclasses import dataclass
from typing import NamedTuple

from fastdjango.core.authentication.exceptions import InvalidCredentialsError
from fastdjango.core.authentication.services.jwt import JWTService
from fastdjango.core.authentication.services.refresh_session import RefreshSessionService
from fastdjango.core.user.models import User
from fastdjango.core.user.use_cases import UserUseCase


@dataclass(kw_only=True)
class TokenUseCase:
    _jwt_service: JWTService
    _refresh_session_service: RefreshSessionService
    _user_use_case: UserUseCase

    def issue_token(
        self,
        *,
        username: str,
        password: str,
        user_agent: str,
        ip_address: str | None,
    ) -> TokenResult:
        user = self._user_use_case.get_user_by_username_and_password(
            username=username,
            password=password,
        )
        if user is None:
            raise InvalidCredentialsError

        refresh_session = self._refresh_session_service.create_refresh_session(
            user=user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return self._build_token_result(
            user=user,
            refresh_token=refresh_session.refresh_token,
        )

    def refresh_token(self, *, refresh_token: str) -> TokenResult:
        rotated_session = self._refresh_session_service.rotate_refresh_token(
            refresh_token=refresh_token,
        )

        return self._build_token_result(
            user=rotated_session.session.user,
            refresh_token=rotated_session.refresh_token,
        )

    def revoke_token(self, *, refresh_token: str, user: User) -> None:
        self._refresh_session_service.revoke_refresh_token(
            refresh_token=refresh_token,
            user=user,
        )

    def _build_token_result(self, *, user: User, refresh_token: str) -> TokenResult:
        return TokenResult(
            access_token=self._jwt_service.issue_access_token(user_id=user.pk),
            refresh_token=refresh_token,
        )


class TokenResult(NamedTuple):
    access_token: str
    refresh_token: str
