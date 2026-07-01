from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, HTTPException

from fastapi_template.core.authentication.delivery.fastapi.schemas.refresh_token_request import (
    RefreshTokenRequestSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.use_cases.refresh_token import RefreshTokenUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class RefreshTokenController(BaseAsyncController):
    """HTTP adapter for rotating refresh tokens and returning a new token pair."""

    _refresh_token_use_case: Injected[RefreshTokenUseCase]

    def register(self, registry: APIRouter) -> None:
        """Attach the refresh-token endpoint to the FastAPI router."""
        registry.add_api_route(
            path="/api/v1/auth/token/refresh",
            endpoint=self.refresh_token,
            methods=["POST"],
            response_model=TokenResponseSchema,
        )

    async def refresh_token(
        self,
        body: RefreshTokenRequestSchema,
    ) -> TokenResponseSchema:
        """Pass a refresh token to the rotation workflow.

        Returns:
            Serialized replacement access and refresh tokens.
        """
        token = await self._refresh_token_use_case.execute(
            data=RefreshTokenDTO(refresh_token=body.refresh_token),
        )

        return TokenResponseSchema.model_validate(token)

    async def handle_exception(self, exception: Exception) -> Any:
        """Translate refresh-token failures into HTTP authentication responses.

        Returns:
            The delegated handler result for unrecognized exceptions.
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
