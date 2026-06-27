from modern_python_template.core.authentication.dtos import IssueTokenDTO, RefreshTokenDTO, TokenDTO
from modern_python_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class IssueTokenRequestSchema(IssueTokenDTO, BaseFastAPISchema):
    pass


class RefreshTokenRequestSchema(RefreshTokenDTO, BaseFastAPISchema):
    pass


class TokenResponseSchema(TokenDTO, BaseFastAPISchema):
    pass
