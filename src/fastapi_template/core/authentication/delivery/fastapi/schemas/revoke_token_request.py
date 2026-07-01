from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class RevokeTokenRequestSchema(BaseFastAPISchema):
    """HTTP request body carrying the refresh token to revoke."""

    refresh_token: str
