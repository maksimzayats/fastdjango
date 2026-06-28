from fastapi_template.core.authentication.dtos import IssueTokenDTO, RefreshTokenDTO, TokenDTO
from fastapi_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class IssueTokenRequestSchema(IssueTokenDTO, BaseFastAPISchema):
    pass


class RefreshTokenRequestSchema(RefreshTokenDTO, BaseFastAPISchema):
    pass


class TokenResponseSchema(TokenDTO, BaseFastAPISchema):
    pass
