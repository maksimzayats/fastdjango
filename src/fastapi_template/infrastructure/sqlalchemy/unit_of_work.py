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
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.infrastructure.sqlalchemy.repositories.user import (
    SQLAlchemyUserRepository,
)
from fastapi_template.core.user.repositories.user import UserRepository
from fastapi_template.infrastructure.sqlalchemy.session import SQLAlchemySessionFactory

_INACTIVE_UOW_ERROR = "Unit of work is not active."
_NESTED_UOW_ERROR = "Nested UnitOfWork scopes are not supported."


@dataclass(frozen=True, kw_only=True)
class _SQLAlchemyUnitOfWorkScope:
    session: AsyncSession
    transaction: AsyncSessionTransaction
    user_repository: UserRepository
    refresh_session_repository: RefreshSessionRepository


def _scope_context_var() -> ContextVar[_SQLAlchemyUnitOfWorkScope | None]:
    return ContextVar("sqlalchemy_unit_of_work_scope", default=None)


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
    scope_context: ContextVar[_SQLAlchemyUnitOfWorkScope | None],
) -> None:
    await scope.session.close()
    scope_context.set(None)


@dataclass(kw_only=True)
class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of the application unit-of-work boundary."""

    _session_factory: Injected[SQLAlchemySessionFactory]

    _scope_context: ContextVar[_SQLAlchemyUnitOfWorkScope | None] = field(
        default_factory=_scope_context_var,
        init=False,
    )

    @property
    def user_repository(self) -> UserRepository:
        """Expose the user repository bound to the active transaction.

        Returns:
            User repository for the current unit-of-work scope.
        """
        return self._current_scope.user_repository

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        """Expose the refresh-session repository bound to the active transaction.

        Returns:
            Refresh-session repository for the current unit-of-work scope.
        """
        return self._current_scope.refresh_session_repository

    async def __aenter__(self) -> UnitOfWork:
        """Enter the async context manager.

        Returns:
        The active context manager.
        """
        if self._scope_context.get() is not None:
            raise RuntimeError(_NESTED_UOW_ERROR)

        session = self._session_factory()
        transaction = await session.begin()
        scope = _SQLAlchemyUnitOfWorkScope(
            session=session,
            transaction=transaction,
            user_repository=SQLAlchemyUserRepository(session=session),
            refresh_session_repository=SQLAlchemyRefreshSessionRepository(session=session),
        )
        self._scope_context.set(scope)

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
        scope = self._scope_context.get()
        if scope is None:
            raise RuntimeError(_INACTIVE_UOW_ERROR)

        try:
            await _finish_transaction(scope=scope, has_error=exc_type is not None)
        except BaseException:
            await _close_scope(
                scope=scope,
                scope_context=self._scope_context,
            )
            raise

        await _close_scope(
            scope=scope,
            scope_context=self._scope_context,
        )

        return False

    @property
    def _current_scope(self) -> _SQLAlchemyUnitOfWorkScope:
        """Active SQLAlchemy session, transaction, and repositories.

        Returns:
            The active SQLAlchemy unit-of-work scope.
        """
        scope = self._scope_context.get()
        if scope is None:
            raise RuntimeError(_INACTIVE_UOW_ERROR)

        return scope
