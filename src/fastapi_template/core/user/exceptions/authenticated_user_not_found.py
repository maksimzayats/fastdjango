from fastapi_template.core.user.exceptions.user import UserError


class AuthenticatedUserNotFoundError(UserError):
    """Raised when the authenticated actor cannot be loaded."""
