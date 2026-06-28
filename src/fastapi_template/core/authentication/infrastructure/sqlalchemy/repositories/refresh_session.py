import uuid
from datetime import datetime

from sqlalchemy import select
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
    """Define SQLAlchemyRefreshSessionRepository."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize the instance."""
        self._session = session

    async def create(self, *, data: CreateRefreshSessionDTO) -> RefreshSession:
        """Create a refresh session.

        Returns:
            The created refresh session.
        """
        model = RefreshSessionModel(
            refresh_token_hash=data.refresh_token_hash,
            user_id=data.user.id,
            user_agent=data.user_agent,
            ip_address_trace=data.ip_address_trace,
            expires_at=data.expires_at,
        )

        self._session.add(model)
        await self._session.flush()

        return refresh_session_from_model(model=model, user=data.user)

    async def get_by_token_hash(self, *, refresh_token_hash: str) -> RefreshSession | None:
        """Get a refresh session by token hash.

        Returns:
            The matching refresh session, if one exists.
        """
        query_result = await self._session.execute(
            select(RefreshSessionModel)
            .options(selectinload(RefreshSessionModel.user))
            .where(RefreshSessionModel.refresh_token_hash == refresh_token_hash),
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
        """Replace the refresh token hash for a session.

        Returns:
            The updated refresh session, if one exists.
        """
        query_result = await self._session.execute(
            select(RefreshSessionModel)
            .options(selectinload(RefreshSessionModel.user))
            .where(
                RefreshSessionModel.id == data.session_id,
                RefreshSessionModel.refresh_token_hash == data.expected_refresh_token_hash,
            )
            .with_for_update(),
        )
        model = query_result.scalar_one_or_none()
        if model is None:
            return None

        model.refresh_token_hash = data.refresh_token_hash
        model.rotation_counter = data.rotation_counter
        model.last_used_at = data.last_used_at

        return refresh_session_from_model(model=model)

    async def revoke(self, *, session_id: uuid.UUID, revoked_at: datetime) -> None:
        """Revoke a refresh session."""
        query_result = await self._session.execute(
            select(RefreshSessionModel)
            .where(RefreshSessionModel.id == session_id)
            .with_for_update(),
        )
        model = query_result.scalar_one_or_none()
        if model is None:
            return

        model.revoked_at = revoked_at
