from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError
from fastapi_template.core.authentication.services.refresh_session import RefreshSessionService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class RevokeTokenUseCase(BaseUseCase):
    """Define RevokeTokenUseCase."""

    INVALID_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR
    REFRESH_TOKEN_ERROR: ClassVar = RefreshTokenError

    _refresh_session_service: Injected[RefreshSessionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RefreshTokenDTO, user: User) -> None:
        """Run execute."""
        async with self._uow as uow:
            await self._refresh_session_service.revoke_refresh_token(
                uow=uow,
                refresh_token=data.refresh_token,
                user=user,
            )
