from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class RefreshTokenRequestSchema(BaseFastAPISchema):
    """HTTP request body carrying the refresh token to rotate."""

    refresh_token: str
