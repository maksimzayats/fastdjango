import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi_template.core.user.entities.user import User


@dataclass(frozen=True, kw_only=True, slots=True)
class RefreshSession:
    """Core refresh-session state used to rotate and revoke refresh tokens."""

    id: uuid.UUID
    refresh_token_hash: str
    user: User
    user_agent: str
    ip_address_trace: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    rotation_counter: int = 0

    def is_active_at(self, *, now: datetime) -> bool:
        """Report whether the refresh session can be used at a known instant.

        Returns:
            ``True`` when the session is neither revoked nor expired.
        """
        return self.revoked_at is None and self.expires_at > now
