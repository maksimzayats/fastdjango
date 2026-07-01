from fastapi_template.core.authentication.exceptions.authentication import AuthenticationError


class InvalidCredentialsError(AuthenticationError):
    """Raised when username and password authentication fails."""
