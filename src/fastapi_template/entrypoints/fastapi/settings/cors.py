from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CORSSettings(BaseSettings):
    """CORS middleware settings loaded from the runtime environment."""

    model_config = SettingsConfigDict(env_prefix="CORS_")

    allow_credentials: bool = True
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
