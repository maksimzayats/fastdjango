from datetime import datetime

from fastapi_template.core.user.entities.user import User
from fastapi_template.foundation.dto import BaseDTO


class CreateRefreshSessionDTO(BaseDTO):
    """Define CreateRefreshSessionDTO."""

    user: User
    refresh_token_hash: str
    user_agent: str
    ip_address_trace: str
    expires_at: datetime
