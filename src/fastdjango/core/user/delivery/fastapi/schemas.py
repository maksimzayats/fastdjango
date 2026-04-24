from fastdjango.core.shared.delivery.fastapi.schemas import Schema
from fastdjango.core.user.dtos import CreateUserDTO, UserDTO


class CreateUserRequestSchema(CreateUserDTO, Schema):
    pass


class UserSchema(UserDTO, Schema):
    pass
