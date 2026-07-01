from fastapi_template.core.application_error import ApplicationError


class UserPermissionDeniedError(ApplicationError):
    """Raised when a user does not satisfy an access policy."""
