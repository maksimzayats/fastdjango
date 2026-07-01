from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError
from fastapi_template.core.authentication.services.refresh_session import RefreshSessionService
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.exceptions.authenticated_user_not_found import (
    AuthenticatedUserNotFoundError,
)
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class RevokeTokenUseCase(BaseUseCase):
    """Revoke a refresh token for an authenticated user."""

    INVALID_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.INVALID_REFRESH_TOKEN_ERROR  # noqa: WPS115
    EXPIRED_REFRESH_TOKEN_ERROR: ClassVar = RefreshSessionService.EXPIRED_REFRESH_TOKEN_ERROR  # noqa: WPS115
    REFRESH_TOKEN_ERROR: ClassVar = RefreshTokenError  # noqa: WPS115
    AUTHENTICATED_USER_NOT_FOUND_ERROR: ClassVar = AuthenticatedUserNotFoundError  # noqa: WPS115

    _refresh_session_service: Injected[RefreshSessionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RefreshTokenDTO, user_id: int) -> None:
        """Load the current user and revoke the submitted refresh token in one UoW."""
        async with self._uow as uow:
            user = await uow.user_repository.get_active_by_id(user_id=user_id)
            if user is None:
                raise self.AUTHENTICATED_USER_NOT_FOUND_ERROR

            await self._refresh_session_service.revoke_refresh_token(
                uow=uow,
                refresh_token=data.refresh_token,
                user=user,
            )
