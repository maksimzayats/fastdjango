from abc import ABC, abstractmethod
from typing import ClassVar

from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.exceptions.user_already_exists import UserAlreadyExistsError


class UserRepository(ABC):
    """Define UserRepository."""

    USER_ALREADY_EXISTS_ERROR: ClassVar = UserAlreadyExistsError

    @abstractmethod
    async def get_by_id(self, *, user_id: int) -> User | None:
        """Get a user by identifier.

        Returns:
            The matching user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_id(self, *, user_id: int) -> User | None:
        """Get an active user by identifier.

        Returns:
            The matching active user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_username(self, *, username: str) -> User | None:
        """Get a user by username.

        Returns:
            The matching user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        """Get a user by username or email.

        Returns:
            The matching user, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, *, data: CreateUserDTO, password_hash: str) -> User:
        """Create a user.

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
        """Set staff and superuser flags.

        Returns:
            The updated user, if one exists.
        """
        raise NotImplementedError
