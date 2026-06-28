from fastapi_template.core.user.exceptions.user import UserError


class WeakPasswordError(UserError):
    """Define WeakPasswordError."""
