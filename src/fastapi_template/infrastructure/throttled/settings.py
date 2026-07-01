from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ThrottledRedisSettings(BaseSettings):
    """Redis connection settings used only by request throttling."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: SecretStr
