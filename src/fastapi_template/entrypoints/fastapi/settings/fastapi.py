from pydantic import Field
from pydantic_settings import BaseSettings


class FastAPISettings(BaseSettings):
    """FastAPI middleware settings loaded from the runtime environment."""

    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
