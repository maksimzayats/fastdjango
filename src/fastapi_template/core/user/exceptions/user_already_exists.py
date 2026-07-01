from fastapi_template.core.user.exceptions.user import UserError


class UserAlreadyExistsError(UserError):
    """Raised when a username or email is already assigned to another user."""
