from dataclasses import dataclass

from diwire import Injected

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class GetActiveUserByIdUseCase(BaseUseCase):
    """Load an active user account by identifier."""

    _uow: Injected[UnitOfWork]

    async def execute(self, *, user_id: int) -> User | None:
        """Fetch an active user inside a unit-of-work scope.

        Returns:
            The active user, if one exists.
        """
        async with self._uow as uow:
            return await uow.user_repository.get_active_by_id(user_id=user_id)
