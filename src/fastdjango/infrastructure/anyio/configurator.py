import logging
from dataclasses import dataclass

from anyio.to_thread import current_default_thread_limiter
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastdjango.foundation.configurators import BaseConfigurator

logger = logging.getLogger(__name__)


class AnyIOSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANYIO_")

    thread_limiter_tokens: int = 40


@dataclass(kw_only=True)
class AnyIOConfigurator(BaseConfigurator):
    _settings: AnyIOSettings

    def configure(self) -> None:
        limiter = current_default_thread_limiter()
        limiter.total_tokens = self._settings.thread_limiter_tokens

        logger.info(
            "Configured AnyIO with thread_limiter_tokens=%d",
            self._settings.thread_limiter_tokens,
        )
