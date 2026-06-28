import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi_template.core.user.entities import User


@dataclass(frozen=True, kw_only=True, slots=True)
class RefreshSession:
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

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > datetime.now(tz=UTC)
