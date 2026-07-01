from fastapi_template.core.application_error import ApplicationError


class AuthenticationError(ApplicationError):
    """Base application error for authentication workflows."""
