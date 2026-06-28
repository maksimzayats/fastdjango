from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException
from throttled import rate_limiter

from fastapi_template.core.authentication.delivery.fastapi.schemas.refresh_token_request import (
    RefreshTokenRequestSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.use_cases.refresh_token import RefreshTokenUseCase
from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler_factory import (
    IPThrottlerFactory,
)
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class RefreshTokenController(BaseAsyncController):
    """Define RefreshTokenController."""

    _ip_throttler_factory: Injected[IPThrottlerFactory]
    _refresh_token_use_case: Injected[RefreshTokenUseCase]

    def register(self, registry: APIRouter) -> None:
        """Run register."""
        registry.add_api_route(
            path="/api/v1/auth/token/refresh",
            endpoint=self.refresh_token,
            methods=["POST"],
            dependencies=[
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
            response_model=TokenResponseSchema,
        )

    async def refresh_token(
        self,
        body: RefreshTokenRequestSchema,
    ) -> TokenResponseSchema:
        """Run refresh token.

        Returns:
        The operation result.
        """
        token = await self._refresh_token_use_case.execute(
            data=RefreshTokenDTO(refresh_token=body.refresh_token),
        )

        return TokenResponseSchema.model_validate(token)

    async def handle_exception(self, exception: Exception) -> Any:
        """Run handle exception.

        Returns:
        The operation result.
        """
        if isinstance(exception, RefreshTokenUseCase.INVALID_REFRESH_TOKEN_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid refresh token",
            ) from exception

        if isinstance(exception, RefreshTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            ) from exception

        if isinstance(exception, RefreshTokenUseCase.REFRESH_TOKEN_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token error",
            ) from exception

        return await super().handle_exception(exception)
