from fastapi_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class IssueTokenRequestSchema(BaseFastAPISchema):
    """Define IssueTokenRequestSchema."""

    username: str
    password: str


class RefreshTokenRequestSchema(BaseFastAPISchema):
    """Define RefreshTokenRequestSchema."""

    refresh_token: str


class TokenResponseSchema(BaseFastAPISchema):
    """Define TokenResponseSchema."""

    access_token: str
    refresh_token: str
