from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, cast

from diwire import Injected
from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.datastructures import State

from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.use_cases import GetActiveUserByIdUseCase
from fastapi_template.foundation.factories import BaseFactory


class AuthenticatedRequestState(State):
    jwt_payload: dict[str, Any]
    user: User


class AuthenticatedRequest(Request):
    state: AuthenticatedRequestState


@dataclass(kw_only=True)
class JWTAuthFactory(BaseFactory):
    """Factory for creating JWT auth instances with optional permission checks.

    Example:
        factory = container.resolve(JWTAuthFactory)
        basic_auth = factory()  # No permission checks
        staff_auth = factory(require_staff=True)  # Requires is_staff=True
        admin_auth = factory(require_superuser=True)  # Requires is_superuser=True
    """

    _jwt_service: Injected[JWTService]
    _get_active_user_by_id_use_case: Injected[GetActiveUserByIdUseCase]

    def __call__(
        self,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> JWTAuth:
        """Create a JWT auth instance.

        Args:
            require_staff: If True, require user.is_staff to be True.
            require_superuser: If True, require user.is_superuser to be True.

        Returns:
            A JWTAuth instance configured with the specified permission checks.
        """
        if require_staff or require_superuser:
            return JWTAuthWithPermissions(
                jwt_service=self._jwt_service,
                get_active_user_by_id_use_case=self._get_active_user_by_id_use_case,
                require_staff=require_staff,
                require_superuser=require_superuser,
            )

        return JWTAuth(
            jwt_service=self._jwt_service,
            get_active_user_by_id_use_case=self._get_active_user_by_id_use_case,
        )


class JWTAuth(HTTPBearer):
    def __init__(
        self,
        jwt_service: JWTService,
        get_active_user_by_id_use_case: GetActiveUserByIdUseCase,
    ) -> None:
        super().__init__()
        self._jwt_service = jwt_service
        self._get_active_user_by_id_use_case = get_active_user_by_id_use_case

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)
        if credentials is None:
            return None

        request = cast(AuthenticatedRequest, request)

        payload = self._get_token_payload(token=credentials.credentials)
        request.state.jwt_payload = payload

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload missing 'sub' field",
            )

        try:
            parsed_user_id = int(user_id)
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload has invalid 'sub' field",
            ) from e

        user = await self._get_active_user_by_id_use_case.execute(user_id=parsed_user_id)

        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="User not found",
            )

        request.state.user = user

        return credentials

    def _get_token_payload(self, token: str) -> dict[str, Any]:
        try:
            return self._jwt_service.decode_token(token=token)
        except self._jwt_service.EXPIRED_SIGNATURE_ERROR as e:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token has expired",
            ) from e
        except self._jwt_service.INVALID_TOKEN_ERROR as e:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid token",
            ) from e


class JWTAuthWithPermissions(JWTAuth):
    """JWT auth with optional is_staff/is_superuser checks."""

    def __init__(
        self,
        jwt_service: JWTService,
        get_active_user_by_id_use_case: GetActiveUserByIdUseCase,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> None:
        super().__init__(
            jwt_service=jwt_service,
            get_active_user_by_id_use_case=get_active_user_by_id_use_case,
        )
        self._require_staff = require_staff
        self._require_superuser = require_superuser

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)

        request = cast(AuthenticatedRequest, request)
        user = request.state.user

        if self._require_staff and not getattr(user, "is_staff", False):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Staff access required",
            )

        if self._require_superuser and not getattr(user, "is_superuser", False):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Superuser access required",
            )

        return credentials
