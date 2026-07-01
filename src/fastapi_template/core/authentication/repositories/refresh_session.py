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
    """Persistence port for refresh-session lifecycle operations."""

    @abstractmethod
    async def create(self, *, data: CreateRefreshSessionDTO) -> RefreshSession:
        """Persist a refresh session within the caller's unit of work.

        Returns:
            The created refresh session.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_token_hash(self, *, refresh_token_hash: str) -> RefreshSession | None:
        """Find a refresh session by hashed token value.

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
        """Replace the token hash when the expected old hash still matches.

        Returns:
            The updated refresh session, if a matching session exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, *, session_id: uuid.UUID, revoked_at: datetime) -> None:
        """Mark a refresh session as revoked in the caller's unit of work."""
        raise NotImplementedError
