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
    """Define RefreshTokenUseCase."""

    INVALID_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR
    REFRESH_TOKEN_ERROR: ClassVar = RefreshTokenError

    _jwt_service: Injected[JWTService]
    _refresh_session_service: Injected[RefreshSessionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RefreshTokenDTO) -> TokenDTO:
        """Run execute.

        Returns:
        The operation result.
        """
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
