from fastdjango.core.authentication.dtos import IssueTokenDTO, RefreshTokenDTO, TokenDTO
from fastdjango.core.shared.delivery.fastapi.schemas import FastAPISchema


class IssueTokenRequestSchema(IssueTokenDTO, FastAPISchema):
    pass


class RefreshTokenRequestSchema(RefreshTokenDTO, FastAPISchema):
    pass


class TokenResponseSchema(TokenDTO, FastAPISchema):
    pass
