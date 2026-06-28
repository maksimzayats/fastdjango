from fastapi_template.core.user.dtos import CreateUserDTO, UserDTO
from fastapi_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class CreateUserRequestSchema(CreateUserDTO, BaseFastAPISchema):
    pass


class UserSchema(UserDTO, BaseFastAPISchema):
    pass
