from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.dtos.token import TokenDTO
from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.authentication.services.refresh_session import RefreshSessionService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class RefreshTokenUseCase(BaseUseCase):
    """Rotate a refresh token and issue a replacement access token."""

    INVALID_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR  # noqa: WPS115
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR  # noqa: WPS115
    REFRESH_TOKEN_ERROR: ClassVar = RefreshTokenError  # noqa: WPS115

    _jwt_service: Injected[JWTService]
    _refresh_session_service: Injected[RefreshSessionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RefreshTokenDTO) -> TokenDTO:
        """Rotate the submitted refresh token inside one unit of work.

        Returns:
            Replacement access and refresh tokens for the session user.
        """
        async with self._uow as uow:
            rotated_session = await self._refresh_session_service.rotate_refresh_token(
                uow=uow,
                refresh_token=data.refresh_token,
            )
            if not rotated_session.session.user.is_active:
                raise self.INVALID_REFRESH_TOKEN_ERROR

            return _build_token_result(
                jwt_service=self._jwt_service,
                user=rotated_session.session.user,
                refresh_token=rotated_session.refresh_token,
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
