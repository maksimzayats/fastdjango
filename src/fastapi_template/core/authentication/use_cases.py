from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.authentication.dtos import (
    IssueTokenDTO,
    RefreshTokenDTO,
    TokenDTO,
    TokenRequestContextDTO,
)
from fastapi_template.core.authentication.exceptions import (
    InvalidCredentialsError,
    RefreshTokenError,
)
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.authentication.services.refresh_session import RefreshSessionService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.services import UserCredentialService
from fastapi_template.foundation.use_cases import BaseUseCase


@dataclass(kw_only=True)
class IssueTokenUseCase(BaseUseCase):
    INVALID_CREDENTIALS_ERROR: ClassVar = InvalidCredentialsError

    _jwt_service: Injected[JWTService]
    _refresh_session_service: Injected[RefreshSessionService]
    _user_credential_service: Injected[UserCredentialService]
    _uow: Injected[UnitOfWork]

    async def execute(
        self,
        *,
        data: IssueTokenDTO,
        context: TokenRequestContextDTO,
    ) -> TokenDTO:
        async with self._uow as uow:
            user = await self._user_credential_service.authenticate_user(
                uow=uow,
                username=data.username,
                password=data.password,
            )
            if user is None:
                raise self.INVALID_CREDENTIALS_ERROR

            refresh_session = await self._refresh_session_service.create_refresh_session(
                uow=uow,
                user=user,
                user_agent=context.user_agent,
                ip_address_trace=context.ip_address_trace,
            )

        return _build_token_result(
            jwt_service=self._jwt_service,
            user=user,
            refresh_token=refresh_session.refresh_token,
        )


@dataclass(kw_only=True)
class RefreshTokenUseCase(BaseUseCase):
    INVALID_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR
    REFRESH_TOKEN_ERROR: ClassVar = RefreshTokenError

    _jwt_service: Injected[JWTService]
    _refresh_session_service: Injected[RefreshSessionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RefreshTokenDTO) -> TokenDTO:
        async with self._uow as uow:
            rotated_session = await self._refresh_session_service.rotate_refresh_token(
                uow=uow,
                refresh_token=data.refresh_token,
            )

        return _build_token_result(
            jwt_service=self._jwt_service,
            user=rotated_session.session.user,
            refresh_token=rotated_session.refresh_token,
        )


@dataclass(kw_only=True)
class RevokeTokenUseCase(BaseUseCase):
    INVALID_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR
    REFRESH_TOKEN_ERROR: ClassVar = RefreshTokenError

    _refresh_session_service: Injected[RefreshSessionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RefreshTokenDTO, user: User) -> None:
        async with self._uow as uow:
            await self._refresh_session_service.revoke_refresh_token(
                uow=uow,
                refresh_token=data.refresh_token,
                user=user,
            )


def _build_token_result(
    *,
    jwt_service: JWTService,
    user: User,
    refresh_token: str,
) -> TokenDTO:
    return TokenDTO(
        access_token=jwt_service.issue_access_token(user_id=user.id),
        refresh_token=refresh_token,
    )
