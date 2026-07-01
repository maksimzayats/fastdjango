from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError


class ExpiredRefreshTokenError(RefreshTokenError):
    """Raised when a refresh session exists but can no longer be used."""
