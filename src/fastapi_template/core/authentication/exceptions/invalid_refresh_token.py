from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError


class InvalidRefreshTokenError(RefreshTokenError):
    """Raised when a refresh token cannot be matched to an active session."""
