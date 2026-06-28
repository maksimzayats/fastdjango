from pydantic_settings import BaseSettings

from fastapi_template.infrastructure.environment import Environment


class ApplicationSettings(BaseSettings):
    """Define ApplicationSettings."""

    environment: Environment = Environment.PRODUCTION
    version: str = "0.1.0"
    time_zone: str = "UTC"
