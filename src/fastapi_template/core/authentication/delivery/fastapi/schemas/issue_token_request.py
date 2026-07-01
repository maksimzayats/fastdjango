from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class IssueTokenRequestSchema(BaseFastAPISchema):
    """HTTP request body accepted by the token issue endpoint."""

    username: str
    password: str
