from http import HTTPStatus
from typing import cast

from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth import JWTAuth
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.user.services.permission import UserPermissionService
from fastapi_template.core.user.use_cases.get_active_user_by_id import (
    GetActiveUserByIdUseCase,
)


class JWTAuthWithPermissions(JWTAuth):
    """JWT auth with optional is_staff/is_superuser checks."""

    def __init__(  # noqa: PLR0913
        self,
        jwt_service: JWTService,
        get_active_user_by_id_use_case: GetActiveUserByIdUseCase,
        user_permission_service: UserPermissionService,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> None:
        """Initialize the instance."""
        super().__init__(
            jwt_service=jwt_service,
            get_active_user_by_id_use_case=get_active_user_by_id_use_case,
        )
        self._user_permission_service = user_permission_service
        self._require_staff = require_staff
        self._require_superuser = require_superuser

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """Run call.

        Returns:
        The operation result.
        """
        credentials = await super().__call__(request)

        request = cast(AuthenticatedRequest, request)
        user = request.state.user

        try:
            self._user_permission_service.check_access(
                user=user,
                require_staff=self._require_staff,
                require_superuser=self._require_superuser,
            )
        except self._user_permission_service.PERMISSION_DENIED_ERROR as exception:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Permission denied",
            ) from exception

        return credentials
