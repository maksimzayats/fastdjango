from fastapi_template.core.user.exceptions.user import UserError


class UserAlreadyExistsError(UserError):
    """Define UserAlreadyExistsError."""
