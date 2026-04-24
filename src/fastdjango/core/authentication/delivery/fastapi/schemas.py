from fastdjango.core.authentication.dtos import IssueTokenDTO, RefreshTokenDTO, TokenDTO
from fastdjango.core.shared.delivery.fastapi.schemas import BaseFastAPISchema


class IssueTokenRequestSchema(IssueTokenDTO, BaseFastAPISchema):
    pass


class RefreshTokenRequestSchema(RefreshTokenDTO, BaseFastAPISchema):
    pass


class TokenResponseSchema(TokenDTO, BaseFastAPISchema):
    pass
