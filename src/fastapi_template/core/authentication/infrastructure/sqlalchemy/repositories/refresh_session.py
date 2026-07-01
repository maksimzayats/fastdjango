import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi_template.core.authentication.dtos.create_refresh_session import (
    CreateRefreshSessionDTO,
)
from fastapi_template.core.authentication.dtos.replace_refresh_session_token import (
    ReplaceRefreshSessionTokenDTO,
)
from fastapi_template.core.authentication.entities.refresh_session import RefreshSession
from fastapi_template.core.authentication.infrastructure.sqlalchemy.mappers.refresh_session import (
    refresh_session_from_model,
)
from fastapi_template.core.authentication.infrastructure.sqlalchemy.models.refresh_session import (
    RefreshSessionModel,
)
from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)


class SQLAlchemyRefreshSessionRepository(RefreshSessionRepository):
    """Refresh-session repository backed by the active SQLAlchemy transaction."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Bind repository queries to an existing unit-of-work session."""
        self._session = session

    async def create(self, *, data: CreateRefreshSessionDTO) -> RefreshSession:
        """Persist a refresh session without committing the transaction.

        Returns:
            The created refresh session.
        """
        model = RefreshSessionModel(
            id=data.id,
            refresh_token_hash=data.refresh_token_hash,
            user_id=data.user.id,
            user_agent=data.user_agent,
            ip_address_trace=data.ip_address_trace,
            created_at=data.created_at,
            last_used_at=data.last_used_at,
            expires_at=data.expires_at,
            revoked_at=data.revoked_at,
            rotation_counter=data.rotation_counter,
        )

        self._session.add(model)
        await self._session.flush()

        return refresh_session_from_model(model=model, user=data.user)

    async def get_by_token_hash(self, *, refresh_token_hash: str) -> RefreshSession | None:
        """Lock and load a refresh session by its hashed token value.

        Returns:
            The matching refresh session, if one exists.
        """
        query_result = await self._session.execute(
            select(RefreshSessionModel)
            .options(selectinload(RefreshSessionModel.user))
            .where(RefreshSessionModel.refresh_token_hash == refresh_token_hash)
            .with_for_update(),
        )
        model = query_result.scalar_one_or_none()

        if model is None:
            return None

        return refresh_session_from_model(model=model)

    async def replace_token_hash(
        self,
        *,
        data: ReplaceRefreshSessionTokenDTO,
    ) -> RefreshSession | None:
        """Rotate a refresh token only if the stored hash still matches.

        Returns:
            The updated refresh session, if a matching session exists.
        """
        update_result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(RefreshSessionModel)
                .where(
                    RefreshSessionModel.id == data.session_id,
                    RefreshSessionModel.refresh_token_hash == data.expected_refresh_token_hash,
                )
                .values(
                    refresh_token_hash=data.refresh_token_hash,
                    last_used_at=data.last_used_at,
                    rotation_counter=data.rotation_counter,
                )
                .execution_options(synchronize_session=False),
            ),
        )
        if update_result.rowcount != 1:
            return None

        query_result = await self._session.execute(
            select(RefreshSessionModel)
            .options(selectinload(RefreshSessionModel.user))
            .where(RefreshSessionModel.refresh_token_hash == data.refresh_token_hash),
        )
        model = query_result.scalar_one()

        return refresh_session_from_model(model=model)

    async def revoke(self, *, session_id: uuid.UUID, revoked_at: datetime) -> None:
        """Mark a refresh session revoked inside the current transaction."""
        query_result = await self._session.execute(
            select(RefreshSessionModel)
            .where(RefreshSessionModel.id == session_id)
            .with_for_update(),
        )
        model = query_result.scalar_one_or_none()
        if model is None:
            return

        model.revoked_at = revoked_at
