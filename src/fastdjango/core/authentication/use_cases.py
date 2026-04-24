from dataclasses import dataclass

from fastdjango.core.authentication.dtos import (
    IssueTokenDTO,
    RefreshTokenDTO,
    TokenDTO,
    TokenRequestContextDTO,
)
from fastdjango.core.authentication.exceptions import InvalidCredentialsError
from fastdjango.core.authentication.services.jwt import JWTService
from fastdjango.core.authentication.services.refresh_session import RefreshSessionService
from fastdjango.core.user.models import User
from fastdjango.core.user.use_cases import UserUseCase
from fastdjango.foundation.use_cases import BaseUseCase


@dataclass(kw_only=True)
class TokenUseCase(BaseUseCase):
    _jwt_service: JWTService
    _refresh_session_service: RefreshSessionService
    _user_use_case: UserUseCase

    def issue_token(
        self,
        *,
        data: IssueTokenDTO,
        context: TokenRequestContextDTO,
    ) -> TokenDTO:
        user = self._user_use_case.get_user_by_username_and_password(
            username=data.username,
            password=data.password,
        )
        if user is None:
            raise InvalidCredentialsError

        refresh_session = self._refresh_session_service.create_refresh_session(
            user=user,
            user_agent=context.user_agent,
            ip_address=context.ip_address,
        )

        return self._build_token_result(
            user=user,
            refresh_token=refresh_session.refresh_token,
        )

    def refresh_token(self, *, data: RefreshTokenDTO) -> TokenDTO:
        rotated_session = self._refresh_session_service.rotate_refresh_token(
            refresh_token=data.refresh_token,
        )

        return self._build_token_result(
            user=rotated_session.session.user,
            refresh_token=rotated_session.refresh_token,
        )

    def revoke_token(self, *, data: RefreshTokenDTO, user: User) -> None:
        self._refresh_session_service.revoke_refresh_token(
            refresh_token=data.refresh_token,
            user=user,
        )

    def _build_token_result(self, *, user: User, refresh_token: str) -> TokenDTO:
        return TokenDTO(
            access_token=self._jwt_service.issue_access_token(user_id=user.pk),
            refresh_token=refresh_token,
        )
