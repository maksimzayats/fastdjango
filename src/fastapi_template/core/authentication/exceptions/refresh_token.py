from fastapi_template.core.authentication.exceptions.authentication import AuthenticationError


class RefreshTokenError(AuthenticationError):
    """Define RefreshTokenError."""
