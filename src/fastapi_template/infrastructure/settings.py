from pydantic_settings import BaseSettings

from fastapi_template.infrastructure.environment import Environment


class ApplicationSettings(BaseSettings):
    """Application-wide runtime settings shared by entrypoints."""

    environment: Environment = Environment.PRODUCTION
    version: str = "0.1.0"
    time_zone: str = "UTC"
