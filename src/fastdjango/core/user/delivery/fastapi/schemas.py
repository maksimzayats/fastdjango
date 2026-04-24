from fastdjango.core.shared.delivery.fastapi.schemas import BaseFastAPISchema
from fastdjango.core.user.dtos import CreateUserDTO, UserDTO


class CreateUserRequestSchema(CreateUserDTO, BaseFastAPISchema):
    pass


class UserSchema(UserDTO, BaseFastAPISchema):
    pass
