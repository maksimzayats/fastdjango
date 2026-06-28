from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.health.repositories.health import HealthRepository
from fastapi_template.core.user.repositories.user import UserRepository


class UnitOfWork(ABC):
    """Define UnitOfWork."""

    @property
    @abstractmethod
    def user_repository(self) -> UserRepository:
        """Return the active user repository.

        Returns:
            The user repository for the current transaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def refresh_session_repository(self) -> RefreshSessionRepository:
        """Return the active refresh-session repository.

        Returns:
            The refresh-session repository for the current transaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def health_repository(self) -> HealthRepository:
        """Return the active health repository.

        Returns:
            The health repository for the current transaction.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        """Enter the unit-of-work transaction.

        Returns:
            The active unit of work.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Exit the unit-of-work transaction.

        Returns:
            Whether the exception was suppressed.
        """
        raise NotImplementedError
