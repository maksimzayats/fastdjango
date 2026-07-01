from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, HTTPException, Request

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
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class IssueTokenController(BaseAsyncController):
    """HTTP adapter for issuing access and refresh tokens from credentials."""

    _request_info_service: Injected[RequestInfoService]
    _issue_token_use_case: Injected[IssueTokenUseCase]

    def register(self, registry: APIRouter) -> None:
        """Attach the token issue endpoint to the FastAPI router."""
        registry.add_api_route(
            path="/api/v1/auth/token",
            endpoint=self.issue_token,
            methods=["POST"],
            response_model=TokenResponseSchema,
        )

    async def issue_token(
        self,
        request: Request,
        body: IssueTokenRequestSchema,
    ) -> TokenResponseSchema:
        """Convert a token request into the credential-authentication use case.

        Returns:
            Serialized access and refresh tokens for the HTTP response.
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
        """Translate token-issue failures into HTTP authentication responses.

        Returns:
            The delegated handler result for unrecognized exceptions.
        """
        if isinstance(exception, IssueTokenUseCase.INVALID_CREDENTIALS_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid username or password",
            ) from exception

        return await super().handle_exception(exception)
