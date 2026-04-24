import logging
import sys
from dataclasses import dataclass

import logfire
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastdjango.infrastructure.configurators import BaseConfigurator
from fastdjango.infrastructure.logfire.configurator import LogfireSettings


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOGGING_")

    level: str = "INFO"
    logfire_settings: LogfireSettings = Field(default_factory=LogfireSettings)


@dataclass(kw_only=True)
class LoggingConfigurator(BaseConfigurator):
    _settings: LoggingSettings

    def configure(self) -> None:
        logging.basicConfig(
            level=self._settings.level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=self._handlers,
        )

        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("diwire._internal").setLevel(logging.WARNING)
        logging.getLogger("opentelemetry.instrumentation.instrumentor").setLevel(logging.ERROR)
        logging.getLogger("s3transfer").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    @property
    def _handlers(self) -> list[logging.Handler]:
        handlers: list[logging.Handler] = [
            logging.StreamHandler(stream=sys.stdout),
        ]

        if self._settings.logfire_settings.is_enabled:
            handlers.append(logfire.LogfireLoggingHandler())

        return handlers
