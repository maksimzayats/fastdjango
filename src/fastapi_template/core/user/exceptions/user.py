from fastapi_template.core.application_error import ApplicationError


class UserError(ApplicationError):
    """Base application error for user workflows."""
