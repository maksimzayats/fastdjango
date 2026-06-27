from modern_python_template.core.user.dtos import CreateUserDTO, UserDTO
from modern_python_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class CreateUserRequestSchema(CreateUserDTO, BaseFastAPISchema):
    pass


class UserSchema(UserDTO, BaseFastAPISchema):
    pass
