import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from fastapi_template.core.authentication.dtos.create_refresh_session import (
    CreateRefreshSessionDTO,
)
from fastapi_template.core.authentication.dtos.replace_refresh_session_token import (
    ReplaceRefreshSessionTokenDTO,
)
from fastapi_template.core.authentication.entities.refresh_session import RefreshSession


class RefreshSessionRepository(ABC):
    """Define RefreshSessionRepository."""

    @abstractmethod
    async def create(self, *, data: CreateRefreshSessionDTO) -> RefreshSession:
        """Create a refresh session.

        Returns:
            The created refresh session.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_token_hash(self, *, refresh_token_hash: str) -> RefreshSession | None:
        """Get a refresh session by token hash.

        Returns:
            The matching refresh session, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def replace_token_hash(
        self,
        *,
        data: ReplaceRefreshSessionTokenDTO,
    ) -> RefreshSession | None:
        """Replace the refresh token hash for a session.

        Returns:
            The updated refresh session, if one exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, *, session_id: uuid.UUID, revoked_at: datetime) -> None:
        """Revoke a refresh session."""
        raise NotImplementedError
