from fastapi_template.core.authentication.exceptions.authentication import AuthenticationError


class RefreshTokenError(AuthenticationError):
    """Base application error for refresh-token lifecycle failures."""
