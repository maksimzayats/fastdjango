from typing import Annotated

from annotated_types import Len
from pydantic import EmailStr

from fastapi_template.core.user.constraints.create_user import (
    PASSWORD_MAX_LENGTH,
    USER_NAME_MAX_LENGTH,
)
from fastapi_template.foundation.dto import BaseDTO


class CreateUserDTO(BaseDTO):
    """Define CreateUserDTO."""

    email: EmailStr
    username: Annotated[str, Len(max_length=USER_NAME_MAX_LENGTH)]
    first_name: Annotated[str, Len(max_length=USER_NAME_MAX_LENGTH)]
    last_name: Annotated[str, Len(max_length=USER_NAME_MAX_LENGTH)]
    password: Annotated[str, Len(max_length=PASSWORD_MAX_LENGTH)]
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
