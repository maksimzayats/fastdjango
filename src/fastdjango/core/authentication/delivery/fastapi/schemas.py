from fastdjango.core.authentication.dtos import IssueTokenDTO, RefreshTokenDTO, TokenDTO
from fastdjango.core.shared.delivery.fastapi.schemas import Schema


class IssueTokenRequestSchema(IssueTokenDTO, Schema):
    pass


class RefreshTokenRequestSchema(RefreshTokenDTO, Schema):
    pass


class TokenResponseSchema(TokenDTO, Schema):
    pass
