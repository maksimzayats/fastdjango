from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class TokenResponseSchema(BaseFastAPISchema):
    """HTTP response body containing the access token and refresh token pair."""

    access_token: str
    refresh_token: str
