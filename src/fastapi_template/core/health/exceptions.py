from fastapi_template.core.exceptions import ApplicationError


class HealthCheckError(ApplicationError):
    pass
