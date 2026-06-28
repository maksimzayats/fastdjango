from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError


class InvalidRefreshTokenError(RefreshTokenError):
    """Define InvalidRefreshTokenError."""
