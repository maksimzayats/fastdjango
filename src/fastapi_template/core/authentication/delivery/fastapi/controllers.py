from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException, Request
from throttled import rate_limiter

from fastapi_template.core.authentication.delivery.fastapi.auth import (
    AuthenticatedRequest,
    JWTAuthFactory,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas import (
    IssueTokenRequestSchema,
    RefreshTokenRequestSchema,
    TokenResponseSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.throttling import UserThrottlerFactory
from fastapi_template.core.authentication.dtos import (
    IssueTokenDTO,
    RefreshTokenDTO,
    TokenRequestContextDTO,
)
from fastapi_template.core.authentication.use_cases import (
    IssueTokenUseCase,
    RefreshTokenUseCase,
    RevokeTokenUseCase,
)
from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoService
from fastapi_template.core.shared.delivery.fastapi.throttling import IPThrottlerFactory
from fastapi_template.foundation.delivery.controllers import BaseAsyncController


@dataclass(kw_only=True)
class AuthenticationTokenController(BaseAsyncController):
    """Define AuthenticationTokenController."""

    _jwt_auth_factory: Injected[JWTAuthFactory]
    _request_info_service: Injected[RequestInfoService]
    _ip_throttler_factory: Injected[IPThrottlerFactory]
    _user_throttler_factory: Injected[UserThrottlerFactory]
    _issue_token_use_case: Injected[IssueTokenUseCase]
    _refresh_token_use_case: Injected[RefreshTokenUseCase]
    _revoke_token_use_case: Injected[RevokeTokenUseCase]

    def __post_init__(self) -> None:
        """Run post init."""
        self._jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Run register."""
        registry.add_api_route(
            path="/api/v1/auth/token",
            endpoint=self.issue_token,
            methods=["POST"],
            dependencies=[
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
            response_model=TokenResponseSchema,
        )

        registry.add_api_route(
            path="/api/v1/auth/token/refresh",
            endpoint=self.refresh_token,
            methods=["POST"],
            dependencies=[
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
            response_model=TokenResponseSchema,
        )

        registry.add_api_route(
            path="/api/v1/auth/token/revoke",
            endpoint=self.revoke_token,
            methods=["POST"],
            dependencies=[
                Depends(self._jwt_auth),
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
                Depends(self._user_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
        )

    async def issue_token(
        self,
        request: Request,
        body: IssueTokenRequestSchema,
    ) -> TokenResponseSchema:
        """Run issue token.

        Returns:
        The operation result.
        """
        token = await self._issue_token_use_case.execute(
            data=IssueTokenDTO(username=body.username, password=body.password),
            context=TokenRequestContextDTO(
                user_agent=self._request_info_service.get_user_agent(request=request),
                ip_address_trace=self._request_info_service.get_user_ip_trace(
                    request=request,
                ),
            ),
        )

        return TokenResponseSchema.model_validate(token)

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

    async def revoke_token(
        self,
        request: AuthenticatedRequest,
        body: RefreshTokenRequestSchema,
    ) -> None:
        """Run revoke token."""
        await self._revoke_token_use_case.execute(
            data=RefreshTokenDTO(refresh_token=body.refresh_token),
            user=request.state.user,
        )

    async def handle_exception(self, exception: Exception) -> Any:
        """Run handle exception.

        Returns:
        The operation result.
        """
        if isinstance(exception, IssueTokenUseCase.INVALID_CREDENTIALS_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid username or password",
            ) from exception

        if isinstance(
            exception,
            (
                RefreshTokenUseCase.INVALID_REFRESH_TOKEN_ERROR,
                RevokeTokenUseCase.INVALID_REFRESH_TOKEN_ERROR,
            ),
        ):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid refresh token",
            ) from exception

        if isinstance(
            exception,
            (
                RefreshTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR,
                RevokeTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR,
            ),
        ):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            ) from exception

        if isinstance(
            exception,
            (
                RefreshTokenUseCase.REFRESH_TOKEN_ERROR,
                RevokeTokenUseCase.REFRESH_TOKEN_ERROR,
            ),
        ):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token error",
            ) from exception

        return await super().handle_exception(exception)
