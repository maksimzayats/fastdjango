from typing import Annotated

from annotated_types import Len
from pydantic import EmailStr

from fastapi_template.core.user.constraints.create_user import (
    PASSWORD_MAX_LENGTH,
    USER_NAME_MAX_LENGTH,
)
from fastapi_template.foundation.delivery.fastapi.schema import BaseFastAPISchema


class CreateUserRequestSchema(BaseFastAPISchema):
    """HTTP request body accepted by the user creation endpoint."""

    email: EmailStr
    username: Annotated[str, Len(max_length=USER_NAME_MAX_LENGTH)]
    first_name: Annotated[str, Len(max_length=USER_NAME_MAX_LENGTH)]
    last_name: Annotated[str, Len(max_length=USER_NAME_MAX_LENGTH)]
    password: Annotated[str, Len(max_length=PASSWORD_MAX_LENGTH)]
