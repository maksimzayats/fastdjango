from fastapi_template.core.application_error import ApplicationError


class HealthCheckError(ApplicationError):
    """Define HealthCheckError."""
