from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.exceptions.authenticated_user_not_found import (
    AuthenticatedUserNotFoundError,
)
from fastapi_template.core.user.services.permission import UserPermissionService
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class StaffUserLookupUseCase(BaseUseCase):
    """Look up a user for an authenticated staff actor."""

    AUTHENTICATED_USER_NOT_FOUND_ERROR: ClassVar = AuthenticatedUserNotFoundError  # noqa: WPS115
    PERMISSION_DENIED_ERROR: ClassVar = UserPermissionService.PERMISSION_DENIED_ERROR  # noqa: WPS115

    _user_permission_service: Injected[UserPermissionService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, user_id: int, actor_user_id: int) -> User | None:
        """Check staff access and load the requested user in one UoW.

        Returns:
            The requested user, if one exists.
        """
        async with self._uow as uow:
            actor = await uow.user_repository.get_active_by_id(user_id=actor_user_id)
            if actor is None:
                raise self.AUTHENTICATED_USER_NOT_FOUND_ERROR

            self._user_permission_service.check_access(
                user=actor,
                require_staff=True,
                require_superuser=False,
            )
            return await uow.user_repository.get_by_id(user_id=user_id)
