from datetime import datetime

from fastapi_template.core.user.entities import User
from fastapi_template.foundation.dtos import BaseDTO


class IssueTokenDTO(BaseDTO):
    username: str
    password: str


class TokenRequestContextDTO(BaseDTO):
    user_agent: str
    ip_address_trace: str | None


class RefreshTokenDTO(BaseDTO):
    refresh_token: str


class CreateRefreshSessionDTO(BaseDTO):
    user: User
    refresh_token_hash: str
    user_agent: str
    ip_address_trace: str
    expires_at: datetime


class TokenDTO(BaseDTO):
    access_token: str
    refresh_token: str
