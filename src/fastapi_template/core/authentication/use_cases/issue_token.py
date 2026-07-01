from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.authentication.dtos.issue_token import IssueTokenDTO
from fastapi_template.core.authentication.dtos.token import TokenDTO
from fastapi_template.core.authentication.dtos.token_request_context import TokenRequestContextDTO
from fastapi_template.core.authentication.exceptions.invalid_credentials import (
    InvalidCredentialsError,
)
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.authentication.services.refresh_session import RefreshSessionService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.services.user_credential import UserCredentialService
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class IssueTokenUseCase(BaseUseCase):
    """Authenticate credentials and issue a fresh access/refresh token pair."""

    INVALID_CREDENTIALS_ERROR: ClassVar = InvalidCredentialsError  # noqa: WPS115

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
        """Authenticate the user and create one refresh session in one UoW.

        Returns:
            Access and refresh tokens for the authenticated user.
        """
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
