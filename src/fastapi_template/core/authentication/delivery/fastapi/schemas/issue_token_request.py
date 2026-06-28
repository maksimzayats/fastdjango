from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class IssueTokenRequestSchema(BaseFastAPISchema):
    """Define IssueTokenRequestSchema."""

    username: str
    password: str
