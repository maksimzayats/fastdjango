from fastdjango.core.shared.delivery.fastapi.schemas import FastAPISchema
from fastdjango.core.user.dtos import CreateUserDTO, UserDTO


class CreateUserRequestSchema(CreateUserDTO, FastAPISchema):
    pass


class UserSchema(UserDTO, FastAPISchema):
    pass
