from fastapi_template.core.user.exceptions.user import UserError


class WeakPasswordError(UserError):
    """Raised when a password fails the project-owned password policy."""
