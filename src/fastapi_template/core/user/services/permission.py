from dataclasses import dataclass
from typing import ClassVar

from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.exceptions.permission_denied import UserPermissionDeniedError
from fastapi_template.foundation.service import BaseService


@dataclass(kw_only=True)
class UserPermissionService(BaseService):
    """Check user access flags for application-level permissions."""

    PERMISSION_DENIED_ERROR: ClassVar = UserPermissionDeniedError  # noqa: WPS115

    def check_access(
        self,
        *,
        user: User,
        require_staff: bool,
        require_superuser: bool,
    ) -> None:
        """Check that a user satisfies the requested access flags."""
        if require_staff and not user.is_staff:
            raise self.PERMISSION_DENIED_ERROR

        if require_superuser and not user.is_superuser:
            raise self.PERMISSION_DENIED_ERROR
