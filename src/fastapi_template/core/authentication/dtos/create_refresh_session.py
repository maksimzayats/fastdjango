import uuid
from datetime import datetime

from fastapi_template.core.user.entities.user import User
from fastapi_template.foundation.dto import BaseDTO


class CreateRefreshSessionDTO(BaseDTO):
    """Core command data for persisting a newly issued refresh session."""

    id: uuid.UUID
    user: User
    refresh_token_hash: str
    user_agent: str
    ip_address_trace: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None
    rotation_counter: int
