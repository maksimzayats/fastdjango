from http import HTTPStatus
from typing import Any, cast

from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.user.use_cases.get_active_user_by_id import (
    GetActiveUserByIdUseCase,
)


class JWTAuth(HTTPBearer):
    """Define JWTAuth."""

    def __init__(
        self,
        jwt_service: JWTService,
        get_active_user_by_id_use_case: GetActiveUserByIdUseCase,
    ) -> None:
        """Initialize the instance."""
        super().__init__()
        self._jwt_service = jwt_service
        self._get_active_user_by_id_use_case = get_active_user_by_id_use_case

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """Run call.

        Returns:
        The operation result.
        """
        credentials = await super().__call__(request)
        if credentials is None:
            return None

        authenticated_request = cast(AuthenticatedRequest, request)

        payload = self._get_token_payload(token=credentials.credentials)
        authenticated_request.state.jwt_payload = payload

        user = await self._get_active_user_by_id_use_case.execute(
            user_id=self._get_subject_user_id(payload=payload),
        )
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="User not found",
            )

        authenticated_request.state.user = user

        return credentials

    def _get_subject_user_id(self, *, payload: dict[str, Any]) -> int:
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload missing 'sub' field",
            )

        try:
            return int(user_id)
        except (TypeError, ValueError) as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload has invalid 'sub' field",
            ) from exception

    def _get_token_payload(self, *, token: str) -> dict[str, Any]:
        try:
            return self._jwt_service.decode_token(token=token)
        except self._jwt_service.EXPIRED_SIGNATURE_ERROR as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token has expired",
            ) from exception
        except self._jwt_service.INVALID_TOKEN_ERROR as exception:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid token",
            ) from exception
