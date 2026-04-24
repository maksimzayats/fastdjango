from typing import Annotated

from annotated_types import Len
from pydantic import EmailStr

from fastdjango.core.shared.dtos import DTO


class CreateUserDTO(DTO):
    email: EmailStr
    username: Annotated[str, Len(max_length=150)]
    first_name: Annotated[str, Len(max_length=150)]
    last_name: Annotated[str, Len(max_length=150)]
    password: Annotated[str, Len(max_length=128)]


class UserDTO(DTO):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_staff: bool
    is_superuser: bool
