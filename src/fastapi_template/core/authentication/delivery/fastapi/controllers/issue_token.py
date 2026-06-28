from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException, Request
from throttled import rate_limiter

from fastapi_template.core.authentication.delivery.fastapi.schemas.issue_token_request import (
    IssueTokenRequestSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.authentication.dtos.issue_token import IssueTokenDTO
from fastapi_template.core.authentication.dtos.token_request_context import TokenRequestContextDTO
from fastapi_template.core.authentication.use_cases.issue_token import IssueTokenUseCase
from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoService
from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler_factory import (
    IPThrottlerFactory,
)
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class IssueTokenController(BaseAsyncController):
    """Define IssueTokenController."""

    _request_info_service: Injected[RequestInfoService]
    _ip_throttler_factory: Injected[IPThrottlerFactory]
    _issue_token_use_case: Injected[IssueTokenUseCase]

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

        return await super().handle_exception(exception)
