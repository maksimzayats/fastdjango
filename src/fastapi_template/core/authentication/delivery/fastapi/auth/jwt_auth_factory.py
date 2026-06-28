from dataclasses import dataclass

from diwire import Injected

from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth import JWTAuth
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_with_permissions import (
    JWTAuthWithPermissions,
)
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.user.services.permission import UserPermissionService
from fastapi_template.core.user.use_cases.get_active_user_by_id import (
    GetActiveUserByIdUseCase,
)
from fastapi_template.foundation.factory import BaseFactory


@dataclass(kw_only=True)
class JWTAuthFactory(BaseFactory):
    """Factory for creating JWT auth instances with optional permission checks."""

    _jwt_service: Injected[JWTService]
    _get_active_user_by_id_use_case: Injected[GetActiveUserByIdUseCase]
    _user_permission_service: Injected[UserPermissionService]

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
                user_permission_service=self._user_permission_service,
                require_staff=require_staff,
                require_superuser=require_superuser,
            )

        return JWTAuth(
            jwt_service=self._jwt_service,
            get_active_user_by_id_use_case=self._get_active_user_by_id_use_case,
        )
