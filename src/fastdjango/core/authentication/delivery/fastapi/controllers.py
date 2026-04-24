from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from throttled import rate_limiter

from fastdjango.core.authentication.delivery.fastapi.auth import (
    AuthenticatedRequest,
    JWTAuthFactory,
)
from fastdjango.core.authentication.delivery.fastapi.schemas import (
    IssueTokenRequestSchema,
    RefreshTokenRequestSchema,
    TokenResponseSchema,
)
from fastdjango.core.authentication.delivery.fastapi.throttling import UserThrottlerFactory
from fastdjango.core.authentication.dtos import TokenRequestContextDTO
from fastdjango.core.authentication.exceptions import (
    ExpiredRefreshTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenError,
)
from fastdjango.core.authentication.use_cases import TokenUseCase
from fastdjango.core.shared.delivery.fastapi.request import RequestInfoService
from fastdjango.core.shared.delivery.fastapi.throttling import IPThrottlerFactory
from fastdjango.infrastructure.delivery.controllers import TransactionController


@dataclass(kw_only=True)
class AuthenticationTokenController(TransactionController):
    _jwt_auth_factory: JWTAuthFactory
    _request_info_service: RequestInfoService
    _ip_throttler_factory: IPThrottlerFactory
    _user_throttler_factory: UserThrottlerFactory
    _token_use_case: TokenUseCase

    def __post_init__(self) -> None:
        self._jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/users/me/token",
            endpoint=self.issue_user_token,
            methods=["POST"],
            dependencies=[
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
            response_model=TokenResponseSchema,
        )

        registry.add_api_route(
            path="/v1/users/me/token/refresh",
            endpoint=self.refresh_user_token,
            methods=["POST"],
            dependencies=[
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
            response_model=TokenResponseSchema,
        )

        registry.add_api_route(
            path="/v1/users/me/token/revoke",
            endpoint=self.revoke_refresh_token,
            methods=["POST"],
            dependencies=[
                Depends(self._jwt_auth),
                Depends(self._ip_throttler_factory(quota=rate_limiter.per_min(10))),
                Depends(self._user_throttler_factory(quota=rate_limiter.per_min(10))),
            ],
        )

    def issue_user_token(
        self,
        request: Request,
        body: IssueTokenRequestSchema,
    ) -> TokenResponseSchema:
        token = self._token_use_case.issue_token(
            data=body,
            context=TokenRequestContextDTO(
                user_agent=self._request_info_service.get_user_agent(request=request),
                ip_address=self._request_info_service.get_user_ip(request=request),
            ),
        )

        return TokenResponseSchema.model_validate(token)

    def refresh_user_token(
        self,
        body: RefreshTokenRequestSchema,
    ) -> TokenResponseSchema:
        token = self._token_use_case.refresh_token(
            data=body,
        )

        return TokenResponseSchema.model_validate(token)

    def revoke_refresh_token(
        self,
        request: AuthenticatedRequest,
        body: RefreshTokenRequestSchema,
    ) -> None:
        self._token_use_case.revoke_token(
            data=body,
            user=request.state.user,
        )

    def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, InvalidCredentialsError):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid username or password",
            ) from exception

        if isinstance(exception, InvalidRefreshTokenError):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid refresh token",
            ) from exception

        if isinstance(exception, ExpiredRefreshTokenError):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            ) from exception

        if isinstance(exception, RefreshTokenError):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Refresh token error",
            ) from exception

        return super().handle_exception(exception)
