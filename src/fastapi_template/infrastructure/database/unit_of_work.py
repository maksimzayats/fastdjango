from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from types import TracebackType

from diwire import Injected
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from fastapi_template.core.authentication.repositories import (
    RefreshSessionRepository,
    SQLAlchemyRefreshSessionRepository,
)
from fastapi_template.core.health.repositories import HealthRepository, SQLAlchemyHealthRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.repositories import SQLAlchemyUserRepository, UserRepository
from fastapi_template.infrastructure.database.session import SQLAlchemySessionFactory

_INACTIVE_UOW_ERROR = "Unit of work is not active."


@dataclass(frozen=True, kw_only=True)
class _SQLAlchemyUnitOfWorkScope:
    session: AsyncSession
    transaction: AsyncSessionTransaction
    user_repository: UserRepository
    refresh_session_repository: RefreshSessionRepository
    health_repository: HealthRepository


def _scope_stack_context_var() -> ContextVar[tuple[_SQLAlchemyUnitOfWorkScope, ...]]:
    return ContextVar("sqlalchemy_unit_of_work_scope", default=())


@dataclass(kw_only=True)
class SQLAlchemyUnitOfWork(UnitOfWork):
    _session_factory: Injected[SQLAlchemySessionFactory]

    _scope_stack: ContextVar[tuple[_SQLAlchemyUnitOfWorkScope, ...]] = field(
        default_factory=_scope_stack_context_var,
        init=False,
    )

    @property
    def user_repository(self) -> UserRepository:
        return self._current_scope.user_repository

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        return self._current_scope.refresh_session_repository

    @property
    def health_repository(self) -> HealthRepository:
        return self._current_scope.health_repository

    async def __aenter__(self) -> UnitOfWork:
        session = self._session_factory()
        transaction = await session.begin()
        scope = _SQLAlchemyUnitOfWorkScope(
            session=session,
            transaction=transaction,
            user_repository=SQLAlchemyUserRepository(session=session),
            refresh_session_repository=SQLAlchemyRefreshSessionRepository(session=session),
            health_repository=SQLAlchemyHealthRepository(session=session),
        )
        self._scope_stack.set((*self._scope_stack.get(), scope))

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        scopes = self._scope_stack.get()
        if not scopes:
            raise RuntimeError(_INACTIVE_UOW_ERROR)

        scope = scopes[-1]
        try:
            if exc_type is None:
                await scope.transaction.commit()
            else:
                await scope.transaction.rollback()
        finally:
            await scope.session.close()
            self._scope_stack.set(scopes[:-1])

        return None

    @property
    def _current_scope(self) -> _SQLAlchemyUnitOfWorkScope:
        scopes = self._scope_stack.get()
        if not scopes:
            raise RuntimeError(_INACTIVE_UOW_ERROR)

        return scopes[-1]
