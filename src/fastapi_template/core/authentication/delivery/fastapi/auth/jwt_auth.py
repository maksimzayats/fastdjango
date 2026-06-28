from http import HTTPStatus
from typing import Any, cast

from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.services.jwt import JWTService

_AUTHENTICATE_HEADER = "WWW-Authenticate"
_BEARER_AUTH_SCHEME = "Bearer"


class JWTAuth(HTTPBearer):
    """Define JWTAuth."""

    def __init__(self, *, jwt_service: JWTService, required: bool = True) -> None:
        """Initialize the instance."""
        super().__init__(auto_error=False)
        self._jwt_service = jwt_service
        self._required = required

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """Run call.

        Returns:
        The operation result.
        """
        credentials = await super().__call__(request)
        if credentials is None:
            if self._required:
                self._raise_missing_credentials()

            return None

        authenticated_request = cast(AuthenticatedRequest, request)

        payload = self._get_token_payload(token=credentials.credentials)
        authenticated_request.state.jwt_payload = payload
        authenticated_request.state.user_id = self._get_subject_user_id(payload=payload)

        return credentials

    def _raise_missing_credentials(self) -> None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Not authenticated",
            headers={_AUTHENTICATE_HEADER: _BEARER_AUTH_SCHEME},
        )

    def _get_subject_user_id(self, *, payload: dict[str, Any]) -> int:
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload missing 'sub' field",
                headers={_AUTHENTICATE_HEADER: _BEARER_AUTH_SCHEME},
            )

        try:
            return int(user_id)
        except (TypeError, ValueError) as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload has invalid 'sub' field",
                headers={_AUTHENTICATE_HEADER: _BEARER_AUTH_SCHEME},
            ) from exception

    def _get_token_payload(self, *, token: str) -> dict[str, Any]:
        try:
            return self._jwt_service.decode_token(token=token)
        except self._jwt_service.EXPIRED_SIGNATURE_ERROR as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token has expired",
                headers={_AUTHENTICATE_HEADER: _BEARER_AUTH_SCHEME},
            ) from exception
        except self._jwt_service.INVALID_TOKEN_ERROR as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid token",
                headers={_AUTHENTICATE_HEADER: _BEARER_AUTH_SCHEME},
            ) from exception
