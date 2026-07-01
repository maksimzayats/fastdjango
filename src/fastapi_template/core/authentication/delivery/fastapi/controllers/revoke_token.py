from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from throttled import rate_limiter

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.bearer_authentication_error import (
    bearer_authentication_error,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.revoke_token_request import (
    RevokeTokenRequestSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler_factory import (
    UserThrottlerFactory,
)
from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.use_cases.revoke_token import RevokeTokenUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class RevokeTokenController(BaseAsyncController):
    """HTTP adapter for revoking a refresh token owned by the current user."""

    _jwt_auth_factory: Injected[JWTAuthFactory]
    _user_throttler_factory: Injected[UserThrottlerFactory]
    _revoke_token_use_case: Injected[RevokeTokenUseCase]

    _jwt_auth: HTTPBearer = field(init=False)

    def __post_init__(self) -> None:
        """Build the reusable JWT dependency before route registration."""
        self._jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Attach the authenticated refresh-token revocation endpoint."""
        registry.add_api_route(
            path="/api/v1/auth/token/revoke",
            endpoint=self.revoke_token,
            methods=["POST"],
            dependencies=[
                Depends(self._jwt_auth),
                Depends(self._user_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
        )

    async def revoke_token(
        self,
        request: AuthenticatedRequest,
        body: RevokeTokenRequestSchema,
    ) -> None:
        """Revoke the submitted refresh token for the authenticated user."""
        await self._revoke_token_use_case.execute(
            data=RefreshTokenDTO(refresh_token=body.refresh_token),
            user_id=request.state.user_id,
        )

    async def handle_exception(self, exception: Exception) -> Any:
        """Translate revocation failures into HTTP authentication responses.

        Returns:
            The delegated handler result for unrecognized exceptions.
        """
        if isinstance(exception, RevokeTokenUseCase.INVALID_REFRESH_TOKEN_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid refresh token",
            ) from exception

        if isinstance(exception, RevokeTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            ) from exception

        if isinstance(exception, RevokeTokenUseCase.REFRESH_TOKEN_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token error",
            ) from exception

        if isinstance(exception, RevokeTokenUseCase.AUTHENTICATED_USER_NOT_FOUND_ERROR):
            raise bearer_authentication_error(detail="User not found") from exception

        return await super().handle_exception(exception)
