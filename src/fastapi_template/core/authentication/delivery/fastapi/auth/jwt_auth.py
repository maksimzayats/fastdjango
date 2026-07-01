from typing import Any, cast

from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.bearer_authentication_error import (
    bearer_authentication_error,
)
from fastapi_template.core.authentication.services.jwt import JWTService


class JWTAuth(HTTPBearer):
    """FastAPI bearer dependency that validates JWTs and stores user identity."""

    def __init__(self, *, jwt_service: JWTService, required: bool = True) -> None:
        """Configure whether missing credentials should reject the request."""
        super().__init__(auto_error=False)
        self._jwt_service = jwt_service
        self._required = required

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """Authenticate the request and attach JWT payload details to state.

        Returns:
            Bearer credentials when a token is present, otherwise ``None`` for
            optional authentication.
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
        raise bearer_authentication_error(detail="Not authenticated")

    def _get_subject_user_id(self, *, payload: dict[str, Any]) -> int:
        user_id = payload.get("sub")
        if user_id is None:
            raise bearer_authentication_error(detail="Token payload missing 'sub' field")

        try:
            return int(user_id)
        except (TypeError, ValueError) as exception:
            raise bearer_authentication_error(
                detail="Token payload has invalid 'sub' field",
            ) from exception

    def _get_token_payload(self, *, token: str) -> dict[str, Any]:
        try:
            return self._jwt_service.decode_token(token=token)
        except self._jwt_service.EXPIRED_SIGNATURE_ERROR as exception:
            raise bearer_authentication_error(detail="Token has expired") from exception
        except self._jwt_service.INVALID_TOKEN_ERROR as exception:
            raise bearer_authentication_error(detail="Invalid token") from exception
