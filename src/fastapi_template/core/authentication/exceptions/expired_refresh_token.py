from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError


class ExpiredRefreshTokenError(RefreshTokenError):
    """Define ExpiredRefreshTokenError."""
