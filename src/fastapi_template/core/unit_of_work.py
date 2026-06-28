from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from fastapi_template.core.authentication.repositories import RefreshSessionRepository
from fastapi_template.core.health.repositories import HealthRepository
from fastapi_template.core.user.repositories import UserRepository


class UnitOfWork(ABC):
    @property
    @abstractmethod
    def user_repository(self) -> UserRepository: ...

    @property
    @abstractmethod
    def refresh_session_repository(self) -> RefreshSessionRepository: ...

    @property
    @abstractmethod
    def health_repository(self) -> HealthRepository: ...

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...
