from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FastAPISettings(BaseSettings):
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_")

    allow_credentials: bool = True
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
