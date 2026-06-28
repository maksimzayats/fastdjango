from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class TokenResponseSchema(BaseFastAPISchema):
    """Define TokenResponseSchema."""

    access_token: str
    refresh_token: str
