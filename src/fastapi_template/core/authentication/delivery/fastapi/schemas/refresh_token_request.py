from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class RefreshTokenRequestSchema(BaseFastAPISchema):
    """Define RefreshTokenRequestSchema."""

    refresh_token: str
