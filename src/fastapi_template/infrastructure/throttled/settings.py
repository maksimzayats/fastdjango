from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ThrottledRedisSettings(BaseSettings):
    """Define ThrottledRedisSettings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: SecretStr
