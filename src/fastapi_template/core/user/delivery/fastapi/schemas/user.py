from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class UserSchema(BaseFastAPISchema):
    """HTTP response body exposing public user account fields."""

    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_staff: bool
    is_superuser: bool
