from fastdjango.core.shared.dtos import DTO


class IssueTokenDTO(DTO):
    username: str
    password: str


class TokenRequestContextDTO(DTO):
    user_agent: str
    ip_address: str | None


class RefreshTokenDTO(DTO):
    refresh_token: str


class TokenDTO(DTO):
    access_token: str
    refresh_token: str
