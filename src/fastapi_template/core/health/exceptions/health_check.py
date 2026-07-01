from fastapi_template.core.application_error import ApplicationError


class HealthCheckError(ApplicationError):
    """Raised when a required readiness dependency is unavailable."""
