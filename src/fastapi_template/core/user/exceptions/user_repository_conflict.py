from fastapi_template.core.user.exceptions.user import UserError


class UserRepositoryConflictError(UserError):
    """Raised when persistence reports a duplicate user constraint."""
