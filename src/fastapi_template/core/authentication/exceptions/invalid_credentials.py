from fastapi_template.core.authentication.exceptions.authentication import AuthenticationError


class InvalidCredentialsError(AuthenticationError):
    """Define InvalidCredentialsError."""
