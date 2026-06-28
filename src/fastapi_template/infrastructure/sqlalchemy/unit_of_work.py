from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from types import TracebackType

from diwire import Injected
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from fastapi_template.core.authentication.infrastructure.sqlalchemy.repositories.refresh_session import (
    SQLAlchemyRefreshSessionRepository,
)
from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.health.infrastructure.sqlalchemy.repositories.health import (
    SQLAlchemyHealthRepository,
)
from fastapi_template.core.health.repositories.health import HealthRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.infrastructure.sqlalchemy.repositories.user import (
    SQLAlchemyUserRepository,
)
from fastapi_template.core.user.repositories.user import UserRepository
from fastapi_template.infrastructure.sqlalchemy.session import SQLAlchemySessionFactory

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


async def _finish_transaction(
    *,
    scope: _SQLAlchemyUnitOfWorkScope,
    has_error: bool,
) -> None:
    if has_error:
        await scope.transaction.rollback()
        return

    await scope.transaction.commit()


async def _close_scope(
    *,
    scope: _SQLAlchemyUnitOfWorkScope,
    scope_stack: ContextVar[tuple[_SQLAlchemyUnitOfWorkScope, ...]],
    remaining_scopes: tuple[_SQLAlchemyUnitOfWorkScope, ...],
) -> None:
    await scope.session.close()
    scope_stack.set(remaining_scopes)


@dataclass(kw_only=True)
class SQLAlchemyUnitOfWork(UnitOfWork):
    """Define SQLAlchemyUnitOfWork."""

    _session_factory: Injected[SQLAlchemySessionFactory]

    _scope_stack: ContextVar[tuple[_SQLAlchemyUnitOfWorkScope, ...]] = field(
        default_factory=_scope_stack_context_var,
        init=False,
    )

    @property
    def user_repository(self) -> UserRepository:
        """Run user repository.

        Returns:
        The operation result.
        """
        return self._current_scope.user_repository

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        """Run refresh session repository.

        Returns:
        The operation result.
        """
        return self._current_scope.refresh_session_repository

    @property
    def health_repository(self) -> HealthRepository:
        """Run health repository.

        Returns:
        The operation result.
        """
        return self._current_scope.health_repository

    async def __aenter__(self) -> UnitOfWork:
        """Enter the async context manager.

        Returns:
        The active context manager.
        """
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
    ) -> bool:
        """Exit the context manager.

        Returns:
            False, so exceptions are never suppressed.
        """
        scopes = self._scope_stack.get()
        if not scopes:
            raise RuntimeError(_INACTIVE_UOW_ERROR)

        scope = scopes[-1]
        try:
            await _finish_transaction(scope=scope, has_error=exc_type is not None)
        except BaseException:
            await _close_scope(
                scope=scope,
                scope_stack=self._scope_stack,
                remaining_scopes=scopes[:-1],
            )
            raise

        await _close_scope(
            scope=scope,
            scope_stack=self._scope_stack,
            remaining_scopes=scopes[:-1],
        )

        return False

    @property
    def _current_scope(self) -> _SQLAlchemyUnitOfWorkScope:
        """Return the current unit-of-work scope.

        Returns:
            The active SQLAlchemy unit-of-work scope.
        """
        scopes = self._scope_stack.get()
        if not scopes:
            raise RuntimeError(_INACTIVE_UOW_ERROR)

        return scopes[-1]
