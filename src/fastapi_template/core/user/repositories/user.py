from abc import ABC, abstractmethod
from typing import ClassVar

from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.exceptions.user_repository_conflict import (
    UserRepositoryConflictError,
)


class UserRepository(ABC):
    """Persistence port for user account lookup and mutation operations."""

    USER_REPOSITORY_CONFLICT_ERROR: ClassVar = UserRepositoryConflictError  # noqa: WPS115

    @abstractmethod
    async def get_by_id(self, *, user_id: int) -> User | None:
        """Find a user account by primary identifier.

        Returns:
            The matching user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_id(self, *, user_id: int) -> User | None:
        """Find a user by identifier only when the account is active.

        Returns:
            The matching active user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_username(self, *, username: str) -> User | None:
        """Find a user account by normalized username.

        Returns:
            The matching user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        """Find a user account by normalized username or email.

        Returns:
            The matching user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, *, data: PersistUserDTO, password_hash: str) -> User:
        """Persist a user account within the caller's unit of work.

        Returns:
            The created user.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_access_flags(
        self,
        *,
        user_id: int,
        is_staff: bool,
        is_superuser: bool,
    ) -> User | None:
        """Update staff and superuser flags for an existing user.

        Returns:
            The updated user, if one exists.
        """
        raise NotImplementedError
