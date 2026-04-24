from fastdjango.core.shared.dtos import BaseDTO


class IssueTokenDTO(BaseDTO):
    username: str
    password: str


class TokenRequestContextDTO(BaseDTO):
    user_agent: str
    ip_address: str | None


class RefreshTokenDTO(BaseDTO):
    refresh_token: str


class TokenDTO(BaseDTO):
    access_token: str
    refresh_token: str
