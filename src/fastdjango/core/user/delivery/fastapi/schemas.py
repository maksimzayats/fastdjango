from fastdjango.core.user.dtos import CreateUserDTO, UserDTO
from fastdjango.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class CreateUserRequestSchema(CreateUserDTO, BaseFastAPISchema):
    pass


class UserSchema(UserDTO, BaseFastAPISchema):
    pass
